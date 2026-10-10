param(
    [Parameter(Mandatory = $true)]
    [string]$PrivateKey,

    [Parameter(Mandatory = $true)]
    [string]$BastionIp,

    [Parameter(Mandatory = $true)]
    [string]$SourcePrivateIp,

    [Parameter(Mandatory = $true)]
    [string]$TargetPrivateIp
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$evidence = Join-Path $repo 'evidence\connectivity\ping-private.txt'

$resolvedKey = (Resolve-Path -LiteralPath $PrivateKey).Path
$command = "ping -c 4 $TargetPrivateIp"
$result = ssh -o StrictHostKeyChecking=accept-new -o "ProxyCommand=ssh -i `"$resolvedKey`" -W %h:%p ec2-user@$BastionIp" -i $resolvedKey "ec2-user@$SourcePrivateIp" $command 2>&1

$header = @(
    'PRUEBA DE CONECTIVIDAD PRIVADA - CC3067 FASE 1'
    "Origen: $SourcePrivateIp (subred Ventas)"
    "Destino: $TargetPrivateIp (subred Ventas)"
    "Bastión: $BastionIp (sólo transporte administrativo)"
    "Fecha local: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
    ''
)

($header + $result) | Set-Content -LiteralPath $evidence -Encoding utf8
$result
Write-Output "Evidencia guardada en: $evidence"
