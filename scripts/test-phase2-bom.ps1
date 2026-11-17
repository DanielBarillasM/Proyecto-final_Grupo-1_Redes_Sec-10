#Requires -Version 5.1
<#
.SYNOPSIS
    Suite de pruebas de aceptación de la Fase 2 (F2-01 a F2-13).
    Implementación: Genser Andree Catalán Espina. Ejecución y evidencia: Pablo Daniel
    Barillas Moreno y Andrés Rafael Chivalán.

.DESCRIPTION
    Ejecuta cada prueba desde su segmento de origen (SSH a través del bastión) o desde el
    equipo del operador (pruebas "desde Internet"), compara el resultado con la matriz de
    tráfico del hand-off y guarda una evidencia de texto por prueba más un resumen.

    No ejecuta terraform, no llama a la API de AWS y no modifica Security Groups, NACL ni
    instancias. Las sondas remotas (scripts/phase2-probe.sh, services/dns/dnsquery.py y
    scripts/check-public-ports.py) se envían por stdin: no se copian a las EC2.

    Veredictos:
      OK       el resultado coincide con la matriz.
      FALLA    contradice la matriz (p. ej. un bloqueo esperado que respondió).
      ERROR    no se pudo ejecutar o hay un problema de configuración/ruta (SSH, DNS, etc.).
      OMITIDA  falta un dato (IP, dominio) o la prueba es opcional y no se habilitó.

    Código de salida: 0 todo OK/OMITIDA, 1 alguna FALLA, 2 algún ERROR sin FALLA.

.EXAMPLE
    pwsh scripts/test-phase2.ps1 -List

.EXAMPLE
    pwsh scripts/test-phase2.ps1 -OutputsJson handoff-retorno/terraform-outputs.json `
        -PrivateKey ~/.ssh/rednova-fase2 -AuthorizedBy "Andrés Rafael Chivalán" -DryRun

.EXAMPLE
    pwsh scripts/test-phase2.ps1 -OutputsJson handoff-retorno/terraform-outputs.json `
        -PrivateKey ~/.ssh/rednova-fase2 -AuthorizedBy "Andrés Rafael Chivalán" -Test 'F2-05*','F2-07*'
#>
[CmdletBinding()]
param(
    # Salida de "terraform output -json" guardada durante la ventana (no contiene secretos).
    [string]$OutputsJson,
    # Llave privada temporal. Nunca se copia ni se registra en la evidencia.
    [string]$PrivateKey,
    # Valores explícitos; tienen prioridad sobre OutputsJson.
    [string]$BastionIp,
    [string]$BastionPrivateIp,
    [string]$VentasIp,
    [string]$VisitasPublicIp,
    [string]$PublicWebIp,
    [string]$PublicDomain,
    [switch]$EnableHttps,
    # IDs o comodines: 'F2-05a', 'F2-09*'. Por defecto, toda la suite.
    [string[]]$Test = @('*'),
    [ValidateRange(1, 60)]
    [int]$TimeoutSeconds = 5,
    # Persona que autorizó la ventana (sección 19.5 del hand-off). Obligatorio salvo -List.
    [string]$AuthorizedBy,
    [switch]$List,
    [switch]$DryRun,
    # Omite la confirmación interactiva (solo si la autorización ya consta por escrito).
    [switch]$Yes,
    [string]$EvidenceDir
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch { }

$repo = Split-Path -Parent $PSScriptRoot
if (-not $EvidenceDir) { $EvidenceDir = Join-Path (Join-Path $repo 'evidence') 'fase-2' }

# --- Contrato de direcciones (hand-off, sección 4.2) -------------------------------
$Ip = [ordered]@{
    visitas  = '10.10.0.4'
    ti       = '10.10.0.132'
    dns      = '10.10.0.164'
    intranet = '10.10.0.165'
    web      = '10.10.0.196'
}
$Rrhh = 'rrhh.rednova.internal'

# --- Datos de la ventana: OutputsJson + parámetros explícitos ----------------------
function Get-TfOutput {
    param($Outputs, [string]$Name, [string[]]$Path = @())
    if ($null -eq $Outputs) { return $null }
    $node = $Outputs.PSObject.Properties[$Name]
    if ($null -eq $node) { return $null }
    $value = $node.Value.value
    foreach ($step in $Path) {
        if ($null -eq $value) { return $null }
        if ($step -match '^\d+$') {
            $arr = @($value); $i = [int]$step
            if ($arr.Count -le $i) { return $null }
            $value = $arr[$i]
        } else {
            $prop = $value.PSObject.Properties[$step]
            $value = if ($prop) { $prop.Value } else { $null }
        }
    }
    return $value
}

$outputs = $null
if ($OutputsJson) {
    $outputs = Get-Content -LiteralPath $OutputsJson -Raw -Encoding UTF8 | ConvertFrom-Json
}
function Pick([string]$Explicit, $FromOutputs) {
    if ($Explicit) { return $Explicit }
    if ($FromOutputs) { return [string]$FromOutputs }
    return $null
}
$BastionIp        = Pick $BastionIp        (Get-TfOutput $outputs 'bastion_public_ip')
$BastionPrivateIp = Pick $BastionPrivateIp (Get-TfOutput $outputs 'test_clients' @('bastion_private_ip'))
$VentasIp         = Pick $VentasIp         (Get-TfOutput $outputs 'ventas_private_ips' @('0'))
$VisitasPublicIp  = Pick $VisitasPublicIp  (Get-TfOutput $outputs 'test_clients' @('visitas', 'public_ip'))
$PublicWebIp      = Pick $PublicWebIp      (Get-TfOutput $outputs 'public_web' @('public_ip'))
$PublicDomain     = Pick $PublicDomain     (Get-TfOutput $outputs 'public_web' @('domain'))
if (-not $EnableHttps -and (Get-TfOutput $outputs 'public_web' @('https')) -eq $true) { $EnableHttps = [switch]::Present }

# Orígenes: IP a la que se entra por SSH (a través del bastión, salvo el propio bastión).
$Origins = @{
    visitas    = @{ Label = 'Visitas (cliente temporal)';      Ip = $Ip.visitas }
    ti         = @{ Label = 'TI (cliente temporal)';           Ip = $Ip.ti }
    ventas     = @{ Label = 'Ventas (instancia de Fase 1)';    Ip = $VentasIp }
    dmz        = @{ Label = 'DMZ (web pública)';               Ip = $Ip.web }
    datacenter = @{ Label = 'Data Center (DNS interno)';       Ip = $Ip.dns }
    admin      = @{ Label = 'Administración (bastión)';        Ip = $BastionPrivateIp; Direct = $true }
    local      = @{ Label = 'Internet (equipo del operador)';  Ip = 'local' }
}

# --- Catálogo de pruebas -------------------------------------------------------------
# Kind: tcp | icmp | http | resolve (sonda bash), dns (dnsquery.py), scan (check-public-ports.py),
#       ltcp | lhttp | lresolve | lscan (desde el equipo local).
$webPorts = if ($EnableHttps) { '80,443' } else { '80' }
function T {
    param($Id, $Group, $Resp, $Origin, $Kind, $Target, $Port, $Expect, $Desc, $Extra = $null, $Optional = $false)
    [pscustomobject]@{
        Id = $Id; Group = $Group; Resp = $Resp; Origin = $Origin; Kind = $Kind; Target = $Target
        Port = $Port; Expect = $Expect; Desc = $Desc; Extra = $Extra; Optional = $Optional
    }
}
$catalog = @(
    T 'F2-01'  'dns'          'Pablo/Andrés Rafael' 'ventas'     'dns'     $Rrhh            53   'permitir' 'Ventas resuelve rrhh.rednova.internal con BIND9' $Ip.intranet
    T 'F2-02'  'dns'          'Pablo/Andrés Rafael' 'ventas'     'http'    "http://$($Ip.intranet)/" 80 'permitir' 'Ventas abre la intranet (HTTP 200)' $Rrhh
    T 'F2-03a' 'connectivity' 'Pablo/Andrés Rafael' 'ti'         'dns'     $Rrhh            53   'permitir' 'TI resuelve rrhh.rednova.internal con BIND9' $Ip.intranet
    T 'F2-03b' 'connectivity' 'Pablo/Andrés Rafael' 'ti'         'http'    "http://$Rrhh/"  80   'permitir' 'TI abre la intranet por nombre (HTTP 200)'
    T 'F2-04'  'dns'          'Pablo/Andrés Rafael' 'admin'      'http'    "http://$($Ip.intranet)/" 80 'permitir' 'Administración abre la intranet (HTTP 200)' $Rrhh
    T 'F2-05a' 'connectivity' 'Pablo/Andrés Rafael' 'visitas'    'http'    "http://$($Ip.intranet)/" 80 'bloquear' 'Visitas NO abre la intranet' $Rrhh
    T 'F2-05b' 'connectivity' 'Pablo/Andrés Rafael' 'visitas'    'dns'     $Rrhh            53   'bloquear' 'Visitas NO consulta el DNS interno'
    T 'F2-05c' 'connectivity' 'Pablo/Andrés Rafael' 'visitas'    'tcp'     $Ip.intranet     22   'bloquear' 'Visitas NO alcanza SSH de la intranet'
    T 'F2-05d' 'connectivity' 'Pablo/Andrés Rafael' 'dmz'        'http'    "http://$($Ip.intranet)/" 80 'bloquear' 'La DMZ NO abre la intranet' $Rrhh
    T 'F2-06'  'security'     'Pablo/Andrés Rafael' 'local'      'lresolve' $Rrhh           53   'bloquear' 'rrhh.rednova.internal no existe en el DNS público'
    T 'F2-07a' 'connectivity' 'Pablo/Andrés Rafael' 'visitas'    'resolve' 'example.com'    53   'permitir' 'Visitas resuelve nombres públicos (resolvedor VPC)'
    T 'F2-07b' 'connectivity' 'Pablo/Andrés Rafael' 'visitas'    'http'    'https://example.com/' 443 'permitir' 'Visitas navega por HTTPS en Internet'
    T 'F2-07c' 'connectivity' 'Pablo/Andrés Rafael' 'visitas'    'http'    'http://example.com/'  80  'permitir' 'Visitas navega por HTTP en Internet'
    T 'F2-08a' 'connectivity' 'Pablo/Andrés Rafael' 'ti'         'icmp'    $Ip.visitas      $null 'permitir' 'TI inicia ICMP hacia Visitas'
    T 'F2-08b' 'connectivity' 'Pablo/Andrés Rafael' 'ti'         'icmp'    $VentasIp        $null 'permitir' 'TI inicia ICMP hacia Ventas'
    T 'F2-08c' 'connectivity' 'Pablo/Andrés Rafael' 'ti'         'icmp'    $BastionPrivateIp $null 'permitir' 'TI inicia ICMP hacia Administración'
    T 'F2-08d' 'connectivity' 'Pablo/Andrés Rafael' 'ti'         'icmp'    $Ip.dns          $null 'permitir' 'TI inicia ICMP hacia Data Center (DNS)'
    T 'F2-08e' 'connectivity' 'Pablo/Andrés Rafael' 'ti'         'tcp'     $Ip.dns          53   'permitir' 'TI inicia TCP/53 hacia el DNS'
    T 'F2-08f' 'connectivity' 'Pablo/Andrés Rafael' 'ti'         'tcp'     $Ip.intranet     80   'permitir' 'TI inicia TCP/80 hacia la intranet'
    T 'F2-08g' 'connectivity' 'Pablo/Andrés Rafael' 'ti'         'icmp'    $Ip.web          $null 'permitir' 'TI inicia ICMP hacia la DMZ'
    T 'F2-08h' 'connectivity' 'Pablo/Andrés Rafael' 'ti'         'http'    "http://$($Ip.web)/" 80 'permitir' 'TI abre la web de la DMZ por IP privada'
    T 'F2-09a' 'connectivity' 'Pablo/Andrés Rafael' 'ventas'     'icmp'    $Ip.ti           $null 'bloquear' 'Ventas NO inicia ICMP hacia TI'
    T 'F2-09b' 'connectivity' 'Pablo/Andrés Rafael' 'ventas'     'tcp'     $Ip.ti           22   'bloquear' 'Ventas NO inicia SSH hacia TI'
    T 'F2-09c' 'connectivity' 'Pablo/Andrés Rafael' 'ventas'     'tcp'     $Ip.ti           8080 'bloquear' 'Ventas NO inicia TCP alto hacia TI (lo detiene el SG)'
    T 'F2-09d' 'connectivity' 'Pablo/Andrés Rafael' 'visitas'    'tcp'     $Ip.ti           22   'bloquear' 'Visitas NO inicia SSH hacia TI'
    T 'F2-09e' 'connectivity' 'Pablo/Andrés Rafael' 'visitas'    'icmp'    $Ip.ti           $null 'bloquear' 'Visitas NO inicia ICMP hacia TI'
    T 'F2-09f' 'connectivity' 'Pablo/Andrés Rafael' 'dmz'        'tcp'     $Ip.ti           22   'bloquear' 'La DMZ NO inicia SSH hacia TI'
    T 'F2-09g' 'connectivity' 'Pablo/Andrés Rafael' 'datacenter' 'tcp'     $Ip.ti           22   'bloquear' 'Data Center NO inicia SSH hacia TI'
    T 'F2-10a' 'public-web'   'Pablo/Andrés Rafael' 'local'      'lhttp'   $(if ($PublicWebIp) { "http://$PublicWebIp/" }) 80 'permitir' 'Web pública por Elastic IP (HTTP 200)'
    T 'F2-10b' 'public-web'   'Pablo/Andrés Rafael' 'local'      'lhttp'   $(if ($PublicDomain) { "http://$PublicDomain/" }) 80 'permitir' 'Web pública por dominio (HTTP 200 o redirección a HTTPS)'
    T 'F2-11a' 'security'     'Pablo/Andrés Rafael' 'local'      'ltcp'    $PublicWebIp     22   'bloquear' 'SSH público hacia la DMZ bloqueado'
    T 'F2-11b' 'security'     'Pablo/Andrés Rafael' 'local'      'ltcp'    $VisitasPublicIp 22   'bloquear' 'SSH público hacia el cliente de Visitas bloqueado'
    T 'F2-12a' 'security'     'Pablo/Andrés Rafael' 'local'      'lscan'   $PublicWebIp     $webPorts 'permitir' "Exterior: en la web solo están abiertos $webPorts"
    T 'F2-12b' 'security'     'Pablo/Andrés Rafael' 'local'      'lscan'   $VisitasPublicIp ''   'permitir' 'Exterior: el cliente de Visitas no expone puertos'
    T 'F2-12c' 'security'     'Pablo/Andrés Rafael' 'ti'         'scan'    $Ip.dns          '53' 'permitir' 'Desde TI: en el DNS solo está abierto 53'
    T 'F2-12d' 'security'     'Pablo/Andrés Rafael' 'ti'         'scan'    $Ip.intranet     '80' 'permitir' 'Desde TI: en la intranet solo está abierto 80'
    T 'F2-12e' 'security'     'Pablo/Andrés Rafael' 'ti'         'scan'    $Ip.web          $webPorts 'permitir' "Desde TI: en la web solo están abiertos $webPorts"
    T 'F2-13a' 'public-web'   'Pablo/Andrés Rafael' 'local'      'lhttp'   $(if ($PublicDomain) { "https://$PublicDomain/" }) 443 'permitir' 'HTTPS con certificado válido (opcional)' $null $true
    T 'F2-13b' 'public-web'   'Pablo/Andrés Rafael' 'local'      'lhttp'   $(if ($PublicDomain) { "http://$PublicDomain/" })  80 'redirigir' 'HTTP redirige a HTTPS (opcional)' $null $true
)

# Con pwsh -File los arreglos llegan como 'a,b': se separan por comas.
$Test = @($Test | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$selected = @($catalog | Where-Object { $id = $_.Id; @($Test | Where-Object { $id -like $_ }).Count -gt 0 })
if ($selected.Count -eq 0) { throw "Ningún ID coincide con: $($Test -join ', '). Use -List para ver el catálogo." }

if ($List) {
    $selected | Format-Table -AutoSize Id, Resp, Origin, Kind, Target, Port, Expect, Desc | Out-String -Width 220 | Write-Output
    exit 0
}

# --- Protocolo AWS (hand-off, sección 19.3) ----------------------------------------------
if (-not $AuthorizedBy) {
    throw 'Indique -AuthorizedBy con la persona que autorizó esta ventana de pruebas (hand-off 19.5).'
}
$needsSsh = @($selected | Where-Object { $_.Origin -ne 'local' }).Count -gt 0
if ($needsSsh) {
    if ($DryRun) {
        if (-not $PrivateKey) { $PrivateKey = '<llave-privada>' }
        if (-not $BastionIp) { $BastionIp = '<bastion>' }
    } else {
        if (-not $PrivateKey) { throw 'Las pruebas remotas requieren -PrivateKey.' }
        if (-not $BastionIp) { throw 'Falta la IP pública del bastión (-BastionIp u OutputsJson).' }
        $PrivateKey = (Resolve-Path -LiteralPath $PrivateKey).Path
    }
}
Write-Host ''
Write-Host 'ATENCIÓN: este paso genera tráfico contra la red real en AWS.' -ForegroundColor Yellow
Write-Host "Confirme que $AuthorizedBy autorizó esta operación concreta (pruebas de conectividad) y" -ForegroundColor Yellow
Write-Host 'entregó por un canal seguro la cuenta, región, llave y ventana. No pegue claves, tokens,' -ForegroundColor Yellow
Write-Host '.tfvars, estados ni llaves privadas en el chat o en Git.' -ForegroundColor Yellow
if (-not $DryRun -and -not $Yes) {
    $answer = Read-Host 'Escriba SI para continuar'
    if ($answer -ne 'SI') { Write-Host 'Cancelado: no se ejecutó ninguna prueba.'; exit 2 }
}

$commit = (& git -C $repo rev-parse --short HEAD 2>$null)
if (-not $commit) { $commit = 'desconocido' }

# --- Utilidades ----------------------------------------------------------------------------
function Read-Payload([string]$RelativePath) {
    $text = Get-Content -LiteralPath (Join-Path $repo $RelativePath) -Raw -Encoding UTF8
    return ($text -replace "`r`n", "`n")
}
$probe = Read-Payload 'scripts/phase2-probe.sh'
$dnsquery = Read-Payload 'services/dns/dnsquery.py'
$portscan = Read-Payload 'scripts/check-public-ports.py'

function Protect-Text([string]$Text) {
    $t = $Text -replace '\b\d{12}\b', '************'
    $t = $t -replace 'AKIA[0-9A-Z]{16}', 'AKIA****************'
    if ($PrivateKey) { $t = $t.Replace($PrivateKey, '<llave-privada>') }
    return $t
}

function Invoke-Remote {
    param([hashtable]$Origin, [string]$Stdin, [string]$Command)
    $ErrorActionPreference = 'Continue'
    $common = @('-i', $PrivateKey, '-o', 'StrictHostKeyChecking=accept-new', '-o', 'ConnectTimeout=15',
                '-o', 'BatchMode=yes', '-o', 'LogLevel=ERROR')
    $sshArgs = @() + $common
    if ($Origin.ContainsKey('Direct') -and $Origin.Direct) {
        $hostIp = $BastionIp
    } else {
        $hostIp = $Origin.Ip
        $proxy = "ssh -i `"$PrivateKey`" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 -o BatchMode=yes -o LogLevel=ERROR -W %h:%p ec2-user@$BastionIp"
        $sshArgs += @('-o', "ProxyCommand=$proxy")
    }
    $sshArgs += @("ec2-user@$hostIp", $Command)
    $shown = "ssh [vía bastión] ec2-user@$($Origin.Ip) '$Command'"
    if ($DryRun) { return @{ Output = "(dry-run) $shown"; Exit = 0; Shown = $shown } }
    $out = $Stdin | & ssh @sshArgs 2>&1 | ForEach-Object { "$_" }
    return @{ Output = ($out -join "`n"); Exit = $LASTEXITCODE; Shown = $shown }
}

function Test-LocalTcp([string]$HostName, [int]$Port, [int]$Seconds) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $task = $client.ConnectAsync($HostName, $Port)
        if (-not $task.Wait([TimeSpan]::FromSeconds($Seconds))) { return 'filtrado' }
        if ($client.Connected) { return 'abierto' }
        return 'error'
    } catch {
        $inner = $_.Exception
        while ($inner.InnerException) { $inner = $inner.InnerException }
        if ($inner -is [System.Net.Sockets.SocketException]) {
            switch ($inner.SocketErrorCode.ToString()) {
                'ConnectionRefused' { return 'rechazado' }
                'TimedOut'          { return 'filtrado' }
                'HostUnreachable'   { return 'sin_ruta' }
                'NetworkUnreachable'{ return 'sin_ruta' }
            }
        }
        return 'error'
    } finally { $client.Close() }
}

function Invoke-LocalHttp([string]$Url, [int]$Seconds) {
    Add-Type -AssemblyName System.Net.Http
    $handler = New-Object System.Net.Http.HttpClientHandler
    $handler.AllowAutoRedirect = $false
    $http = New-Object System.Net.Http.HttpClient($handler)
    $http.Timeout = [TimeSpan]::FromSeconds($Seconds * 2)
    try {
        $resp = $http.GetAsync($Url).GetAwaiter().GetResult()
        $code = [int]$resp.StatusCode
        $loc = if ($resp.Headers.Location) { [string]$resp.Headers.Location } else { '' }
        return @{ Result = "http_$code"; Detail = "HTTP $code $($resp.ReasonPhrase)`nServer: $($resp.Headers.Server)`nLocation: $loc"; Location = $loc }
    } catch {
        $inner = $_.Exception
        while ($inner.InnerException) { $inner = $inner.InnerException }
        $msg = $inner.Message
        $r = 'error'
        if ($inner -is [System.Threading.Tasks.TaskCanceledException] -or $msg -match 'timed out|tiempo') { $r = 'filtrado' }
        elseif ($msg -match 'refused|rechaz') { $r = 'rechazado' }
        elseif ($msg -match 'certificate|SSL|TLS') { $r = 'tls_invalido' }
        elseif ($msg -match 'resolve|name|host') { $r = 'dns_fallo' }
        return @{ Result = $r; Detail = "$($inner.GetType().Name): $msg"; Location = '' }
    } finally { $http.Dispose() }
}

$DefaultPorts = 21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995,
                1433, 3306, 3389, 5432, 5900, 6379, 8080, 8443, 27017

# --- Ejecución de una prueba ----------------------------------------------------------------
function Invoke-Phase2Test($t) {
    $origin = $Origins[$t.Origin]
    $rec = [ordered]@{
        Id = $t.Id; Descripcion = $t.Desc; Responsable = $t.Resp
        Fecha = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss zzz'); Commit = $commit; AutorizadoPor = $AuthorizedBy
        Origen = $origin.Label; IpOrigen = $origin.Ip
        Destino = $t.Target; Puerto = $t.Port; Comando = ''; Esperado = $t.Expect
        Obtenido = ''; Veredicto = ''; Nota = ''; Salida = ''
    }
    if ($t.Optional -and -not $EnableHttps) {
        $rec.Veredicto = 'OMITIDA'; $rec.Nota = 'Prueba opcional: HTTPS no habilitado (enable_https = false).'
        return [pscustomobject]$rec
    }
    if (-not $t.Target -or ($t.Origin -ne 'local' -and -not $origin.Ip)) {
        $rec.Veredicto = 'OMITIDA'; $rec.Nota = 'Falta un dato de la ventana (IP o dominio): revise OutputsJson o los parámetros.'
        return [pscustomobject]$rec
    }

    $result = ''; $output = ''
    $to = $TimeoutSeconds
    switch ($t.Kind) {
        { $_ -in 'tcp', 'icmp', 'http', 'resolve' } {
            $cmdArgs = switch ($t.Kind) {
                'tcp'     { "tcp $($t.Target) $($t.Port) $to" }
                'icmp'    { "icmp $($t.Target) $to" }
                'http'    { if ($t.Extra) { "http $($t.Target) $to $($t.Extra)" } else { "http $($t.Target) $to" } }
                'resolve' { "resolve $($t.Target)" }
            }
            $r = Invoke-Remote -Origin $origin -Stdin $probe -Command "bash -s -- $cmdArgs"
            $rec.Comando = $r.Shown; $output = $r.Output
            $m = [regex]::Match($output, 'RESULTADO=(\S+)')
            $result = if ($m.Success) { $m.Groups[1].Value } elseif ($DryRun) { 'dry-run' } else { "ssh_error_$($r.Exit)" }
        }
        'dns' {
            $r = Invoke-Remote -Origin $origin -Stdin $dnsquery -Command "python3 - $($t.Target) $($Ip.dns) --timeout $to"
            $rec.Comando = $r.Shown; $output = $r.Output
            $result = switch ($r.Exit) {
                0 { if ($t.Extra -and $output -notmatch [regex]::Escape($t.Extra)) { 'respuesta_incorrecta' } else { 'resuelto' } }
                2 { 'tiempo_agotado' }
                1 { 'sin_respuesta_valida' }
                255 { 'ssh_error_255' }
                default { "error_$($r.Exit)" }
            }
            if ($DryRun) { $result = 'dry-run' }
        }
        'scan' {
            $r = Invoke-Remote -Origin $origin -Stdin $portscan -Command "python3 - $($t.Target) --expect-open '$($t.Port)' --timeout 2"
            $rec.Comando = $r.Shown; $output = $r.Output
            $result = switch ($r.Exit) { 0 { 'conforme' } 1 { 'no_conforme' } default { "ssh_error_$($r.Exit)" } }
            if ($DryRun) { $result = 'dry-run' }
        }
        'ltcp' {
            $rec.Comando = "TcpClient.ConnectAsync($($t.Target), $($t.Port)) timeout $to s"
            $result = if ($DryRun) { 'dry-run' } else { Test-LocalTcp $t.Target ([int]$t.Port) $to }
            $output = "Conexión TCP local a $($t.Target):$($t.Port) -> $result"
        }
        'lhttp' {
            $rec.Comando = "HttpClient GET $($t.Target) (sin seguir redirecciones)"
            if ($DryRun) { $result = 'dry-run' } else {
                $h = Invoke-LocalHttp $t.Target $to
                $result = $h.Result; $output = $h.Detail
                if ($t.Expect -eq 'redirigir' -and $result -match '^http_30[1278]$' -and $h.Location -notmatch '^https://') {
                    $result = 'redireccion_no_https'
                }
            }
        }
        'lresolve' {
            $rec.Comando = "[System.Net.Dns]::GetHostAddresses('$($t.Target)')"
            if ($DryRun) { $result = 'dry-run' } else {
                try {
                    $addrs = [System.Net.Dns]::GetHostAddresses($t.Target)
                    $result = 'resuelto'; $output = ($addrs | ForEach-Object { $_.IPAddressToString }) -join ', '
                } catch { $result = 'no_resuelto'; $output = $_.Exception.Message }
            }
        }
        'lscan' {
            $expected = @(([string]$t.Port).Split(',') | Where-Object { $_ } | ForEach-Object { [int]$_ })
            $ports = @($DefaultPorts + $expected | Sort-Object -Unique)
            $rec.Comando = "Escaneo TCP local de $($ports.Count) puertos en $($t.Target) (timeout 2 s)"
            if ($DryRun) { $result = 'dry-run' } else {
                $lines = @("PUERTO  OBTENIDO   ESPERADO    RESULTADO"); $bad = 0
                foreach ($p in $ports) {
                    $got = Test-LocalTcp $t.Target $p 2
                    $want = if ($expected -contains $p) { 'abierto' } else { 'no-abierto' }
                    $ok = if ($expected -contains $p) { $got -eq 'abierto' } else { $got -ne 'abierto' }
                    if (-not $ok) { $bad++ }
                    $lines += ('{0,6}  {1,-10} {2,-11} {3}' -f $p, $got, $want, $(if ($ok) { 'OK' } else { 'FALLA' }))
                }
                $output = $lines -join "`n"
                $result = if ($bad -eq 0) { 'conforme' } else { 'no_conforme' }
            }
        }
    }

    # --- Veredicto contra la matriz --------------------------------------------------------
    $allow = @{
        tcp = @('abierto'); icmp = @('respuesta'); resolve = @('resuelto*'); dns = @('resuelto')
        scan = @('conforme'); lscan = @('conforme'); ltcp = @('abierto'); lresolve = @('resuelto')
    }
    $block = @{
        tcp = @('filtrado'); icmp = @('sin_respuesta'); http = @('filtrado'); dns = @('tiempo_agotado')
        resolve = @('no_resuelto'); ltcp = @('filtrado', 'rechazado'); lresolve = @('no_resuelto'); lhttp = @('filtrado')
    }
    # Respuestas que demuestran que el tráfico llegó al destino aunque se esperaba bloqueo.
    $reached = @('abierto', 'rechazado', 'respuesta', 'resuelto', 'http_*')
    $verdict = 'ERROR'; $note = ''
    if ($result -eq 'dry-run') { $verdict = 'DRY-RUN' }
    elseif ($result -like 'ssh_error_*') { $note = 'No se pudo entrar al origen por SSH (bastión, llave o SG de administración).' }
    elseif ($t.Expect -eq 'permitir') {
        $okList = if ($t.Kind -in 'http', 'lhttp') {
            if ($t.Target -match 'rednova\.internal|10\.10\.0\.165') { @('http_200') } else { @('http_2*', 'http_3*') }
        } else { $allow[$t.Kind] }
        if (@($okList | Where-Object { $result -like $_ }).Count -gt 0) { $verdict = 'OK' }
        elseif ($result -in 'filtrado', 'sin_respuesta', 'tiempo_agotado', 'no_conforme', 'rechazado', 'respuesta_incorrecta', 'http_403', 'http_404', 'http_5*') {
            $verdict = 'FALLA'; $note = 'Se esperaba acceso permitido.'
        } elseif ($result -like 'http_*') { $verdict = 'FALLA'; $note = 'Código HTTP distinto del esperado.' }
        else { $note = 'Resultado de configuración o ruta (DNS, ruta, TLS); revise antes de concluir.' }
    }
    elseif ($t.Expect -eq 'bloquear') {
        if (@($block[$t.Kind] | Where-Object { $result -like $_ }).Count -gt 0) {
            $verdict = 'OK'
            if ($result -eq 'rechazado') { $note = 'El destino respondió RST: puerto cerrado, sin servicio expuesto.' }
        }
        elseif (@($reached | Where-Object { $result -like $_ }).Count -gt 0) {
            $verdict = 'FALLA'; $note = 'El tráfico llegó al destino: el filtrado de red no actuó.'
        }
        else { $note = 'No es un bloqueo concluyente (posible falta de ruta o error); no se cuenta como OK.' }
    }
    elseif ($t.Expect -eq 'redirigir') {
        if ($result -match '^http_30[1278]$') { $verdict = 'OK' }
        elseif ($result -like 'http_*' -or $result -eq 'redireccion_no_https') { $verdict = 'FALLA'; $note = 'HTTP no redirige a HTTPS.' }
    }
    if ($result -like 'http_*' -and $t.Kind -eq 'http' -and $t.Expect -eq 'bloquear') { $verdict = 'FALLA' }

    $rec.Obtenido = $result; $rec.Veredicto = $verdict; $rec.Nota = $note
    $rec.Salida = Protect-Text $output
    return [pscustomobject]$rec
}

# --- Ejecución de la suite ------------------------------------------------------------------
$results = @()
foreach ($t in $selected) {
    Write-Host ("[{0}] {1} ..." -f $t.Id, $t.Desc) -NoNewline
    $res = Invoke-Phase2Test $t
    $color = switch ($res.Veredicto) { 'OK' { 'Green' } 'FALLA' { 'Red' } 'ERROR' { 'Magenta' } default { 'Gray' } }
    Write-Host (" {0} ({1})" -f $res.Veredicto, $res.Obtenido) -ForegroundColor $color
    if ($DryRun -and $res.Comando) { Write-Host "    $($res.Comando)" -ForegroundColor DarkGray }
    $results += $res
}

if (-not $DryRun) {
    foreach ($r in $results) {
        $t = $catalog | Where-Object Id -eq $r.Id
        $dir = Join-Path $EvidenceDir $t.Group
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        $body = @(
            "PRUEBA $($r.Id) - $($r.Descripcion)"
            "Responsable: $($r.Responsable)"
            "Fecha local: $($r.Fecha)"
            "Commit: $($r.Commit)"
            "Autorizado por: $($r.AutorizadoPor)"
            "Origen: $($r.Origen) [$($r.IpOrigen)]"
            "Destino: $($r.Destino)$(if ($r.Puerto) { " puerto $($r.Puerto)" })"
            "Comando: $($r.Comando)"
            "Esperado: $($r.Esperado)"
            "Obtenido: $($r.Obtenido)"
            "Veredicto: $($r.Veredicto)"
            "Nota: $($r.Nota)"
            ''
            '--- Salida ---'
            $r.Salida
        )
        ($body -join "`n") + "`n" | Set-Content -LiteralPath (Join-Path $dir "$($r.Id).txt") -Encoding UTF8 -NoNewline
    }
    New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
    $summaryPath = Join-Path $EvidenceDir 'pruebas-fase2.txt'
    $header = @(
        'MATRIZ DE PRUEBAS - CC3067 FASE 2 - GRUPO 1'
        "Fecha local: $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss zzz'))"
        "Commit: $commit"
        "Autorizado por: $AuthorizedBy"
        "Bastión: $(if ($BastionIp) { $BastionIp } else { 'n/d' })   Web pública: $(if ($PublicWebIp) { $PublicWebIp } else { 'n/d' })   Dominio: $(if ($PublicDomain) { $PublicDomain } else { 'n/d' })"
        ''
    )
    $table = $results | Format-Table -AutoSize Id, Origen, Destino, Puerto, Esperado, Obtenido, Veredicto, Responsable |
             Out-String -Width 220
    $counts = $results | Group-Object Veredicto | ForEach-Object { "$($_.Name)=$($_.Count)" }
    (Protect-Text (($header -join "`n") + $table + "Totales: $($counts -join ', ')`n")) |
        Set-Content -LiteralPath $summaryPath -Encoding UTF8 -NoNewline
    $results | Select-Object Id, Fecha, Commit, Origen, IpOrigen, Destino, Puerto, Comando, Esperado, Obtenido, Veredicto, Responsable, Nota |
        Export-Csv -LiteralPath (Join-Path $EvidenceDir 'pruebas-fase2.csv') -NoTypeInformation -Encoding UTF8
    Write-Host ''
    Write-Host ("Evidencias por prueba en: " + (Join-Path (Join-Path $EvidenceDir "<grupo>") "<ID>.txt"))
    Write-Host "Resumen: $summaryPath"
}

$fail = @($results | Where-Object Veredicto -eq 'FALLA').Count
$err = @($results | Where-Object Veredicto -eq 'ERROR').Count
Write-Host ("Totales: OK={0} FALLA={1} ERROR={2} OMITIDA={3}" -f
    @($results | Where-Object Veredicto -eq 'OK').Count, $fail, $err, @($results | Where-Object Veredicto -eq 'OMITIDA').Count)
if ($fail -gt 0) { exit 1 }
if ($err -gt 0) { exit 2 }
exit 0
