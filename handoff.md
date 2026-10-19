# Handoff — Fase 1 del Proyecto Final de Redes

## 1. Propósito del traspaso

Este documento permite que otro agente y el equipo continúen el proyecto sin perder decisiones, contexto ni controles de seguridad. La parte documental está desarrollada y validada localmente; falta ejecutar una ventana breve de laboratorio en una cuenta AWS autorizada para cerrar tres requisitos:

1. implementar realmente el prototipo con Terraform;
2. conservar capturas auténticas de la infraestructura creada;
3. demostrar conectividad ICMP entre las dos instancias privadas de Ventas.

La evidencia debe provenir de una ejecución real. No se deben fabricar capturas, identificadores, salidas de Terraform ni resultados de ping.

## 2. Estado actual

- Último commit publicado antes de estas correcciones: `235158d` en `main`.
- Existen cambios locales posteriores que todavía deben revisarse antes de hacer commit o push.
- PDF actual: `output/pdf/Proyecto_Final_Fase_1_Grupo_1.pdf`.
- Auditoría: `docs/fase-1/AUDITORIA_FINAL.md`.
- Infraestructura: `infra/terraform/`.
- Prueba de conectividad: `scripts/test-connectivity.ps1`.
- Evidencias: `evidence/`.

El siguiente agente debe comenzar con:

```powershell
git status --short --branch
git diff --check
```

No debe ejecutar `git reset --hard`, borrar el estado Terraform ni sobrescribir cambios locales.

## 3. Idea y arquitectura acordadas

La empresa ficticia RedNova GT se implementa en una VPC `10.10.0.0/24` en AWS. El diseño contiene cinco segmentos y un bloque de reserva:

| Segmento | CIDR | Uso | Exposición |
|---|---:|---|---|
| Visitas | `10.10.0.0/26` | 30 visitantes concurrentes asumidos | Subred asociada a tabla pública, sin clientes desplegados |
| Ventas | `10.10.0.64/26` | 25 usuarios y dos EC2 de prueba | Privada |
| TI | `10.10.0.128/27` | 15 usuarios | Privada |
| Data Center | `10.10.0.160/28` | 5 servidores | Privada |
| Administración | `10.10.0.176/28` | Bastión temporal | Pública |
| Reserva | `10.10.0.192/26` | Crecimiento | No desplegada como subred |

Terraform crea:

- una VPC;
- cinco subredes;
- un Internet Gateway;
- una tabla pública y una privada;
- cinco asociaciones de tablas de rutas;
- un grupo de seguridad para el bastión;
- un grupo de seguridad para Ventas;
- una llave EC2 temporal;
- un bastión con IP pública;
- dos instancias privadas de Ventas.

No se usa NAT Gateway. `map_public_ip_on_launch` está desactivado en todas las subredes. Sólo el bastión solicita una IPv4 pública. SSH al bastión debe limitarse a la IPv4 real del operador con prefijo `/32`; nunca se debe abrir `22/tcp` a `0.0.0.0/0`.

## 4. Responsabilidades

### Usuario o integrante del equipo

El usuario humano debe:

- proporcionar una cuenta AWS autorizada o iniciar el laboratorio académico;
- confirmar que existen créditos o presupuesto y aceptar el costo temporal;
- configurar las credenciales localmente, nunca en el chat o repositorio;
- confirmar la cuenta y región antes del `apply`;
- permanecer disponible hasta terminar la destrucción;
- tomar o validar las capturas de AWS Console.

### Agente que continúa

El agente debe:

- inspeccionar el repositorio y no descartar cambios existentes;
- ejecutar primero comprobaciones de sólo lectura;
- mostrar al usuario el resumen del `terraform plan`;
- solicitar confirmación explícita antes de `terraform apply` si el usuario no la ha dado para esa cuenta y ventana de costos;
- conservar evidencia textual y visual;
- ejecutar y verificar la destrucción en la misma sesión;
- renovar credenciales temporales si expiran antes de destruir;
- detenerse ante recursos inesperados, otra cuenta, otra región o permisos insuficientes.

## 5. Prerrequisitos en Windows

Comprobar desde PowerShell:

```powershell
aws --version
terraform version
ssh -V
python --version
```

Se necesita:

- AWS CLI v2;
- Terraform `>= 1.6.0`;
- OpenSSH Client de Windows;
- Python 3;
- acceso a AWS Console para las capturas.

Si falta AWS CLI, instalarlo únicamente desde la [guía oficial de AWS CLI para Windows](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html). Si falta Terraform, seguir la [guía oficial de instalación de Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli).

La cuenta necesita permisos para administrar los recursos EC2/VPC usados por el código: VPC, subredes, rutas, Internet Gateway, grupos de seguridad, llaves EC2, tres instancias, etiquetas y volúmenes raíz. En un laboratorio administrado, no se deben ampliar permisos por cuenta propia; ante `AccessDenied`, pedir ayuda al docente o administrador.

## 6. Configurar autenticación AWS

### Opción A - AWS IAM Identity Center / SSO (preferida)

El administrador debe entregar la URL de inicio, región SSO, cuenta y rol. Ejecutar:

```powershell
aws configure sso --profile cc3067-fase1
aws sso login --profile cc3067-fase1
$env:AWS_PROFILE = "cc3067-fase1"
$env:AWS_REGION = "us-east-1"
aws sts get-caller-identity
aws configure get region --profile cc3067-fase1
```

`aws configure sso` crea un perfil que obtiene credenciales temporales. No se debe copiar ningún token al repositorio. Referencia: [configuración SSO oficial](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html).

### Opción B - Credenciales temporales de un laboratorio académico

1. Iniciar el laboratorio y esperar a que indique que está listo.
2. Abrir los detalles de AWS y copiar el bloque de credenciales temporales.
3. Guardarlo únicamente en `%USERPROFILE%\.aws\credentials`, bajo un perfil como `[cc3067-fase1]`.
4. No guardar ese bloque dentro del proyecto, una captura, un mensaje o un documento.
5. Activar el perfil y verificarlo:

```powershell
$env:AWS_PROFILE = "cc3067-fase1"
$env:AWS_REGION = "us-east-1"
aws sts get-caller-identity
```

El perfil temporal necesita los tres valores: `aws_access_key_id`, `aws_secret_access_key` y `aws_session_token`. Si aparece `ExpiredToken`, renovar los tres antes de continuar. Nunca eliminar `terraform.tfstate` para solucionar una expiración; renovar la sesión y destruir normalmente.

### Puerta de seguridad de identidad

Antes de crear recursos, el usuario debe reconocer la cuenta y el ARN mostrados por:

```powershell
aws sts get-caller-identity
```

Si la cuenta no es la esperada, detenerse. El comando no revela claves secretas; aun así, el ID de cuenta puede ocultarse parcialmente en la copia que vaya al informe.

## 7. Preparar variables y llave SSH temporal

Desde PowerShell:

```powershell
$repo = "C:\Users\Daniel Barillas\Desktop\Proyecto-Final_Redes\Proyecto-final_Grupo-1_Redes_Sec-10"
New-Item -ItemType Directory -Force -Path "$repo\tmp" | Out-Null

$publicIp = (Invoke-RestMethod -Uri "https://checkip.amazonaws.com").Trim()
Write-Output "IP administrativa: $publicIp/32"

ssh-keygen -t ed25519 -f "$repo\tmp\rednova-fase1" -C "cc3067-fase1"

Set-Location "$repo\infra\terraform"
Copy-Item -LiteralPath ".\terraform.tfvars.example" -Destination ".\terraform.tfvars" -Force
notepad .\terraform.tfvars
```

Al ejecutar `ssh-keygen`, se puede usar una contraseña y cargar la llave en `ssh-agent`, o dejarla vacía únicamente para esta ventana corta de laboratorio. La llave privada `tmp/rednova-fase1` y `terraform.tfvars` están excluidos de Git.

Editar `terraform.tfvars`:

```hcl
aws_region      = "us-east-1"
enable_compute  = true
admin_cidr      = "IP_PUBLICA_REAL/32"
public_key_path = "../../tmp/rednova-fase1.pub"
instance_type   = "t3.micro"
```

Antes del despliegue:

- sustituir `IP_PUBLICA_REAL`;
- confirmar que VPN o cambio de red no alterarán esa IP;
- mantener `/32`;
- comprobar que `tmp/rednova-fase1.pub` existe;
- actualizar `DeleteAfter` en `infra/terraform/locals.tf` si la fecha de destrucción ya no es `2026-10-19`;
- confirmar que la región permite tres instancias del tipo seleccionado.

No se debe asumir que `t3.micro`, EBS o la IPv4 pública son gratuitos. Consultar el presupuesto o créditos de la cuenta antes del `apply`.

## 8. Validar y revisar el plan

```powershell
$repo = "C:\Users\Daniel Barillas\Desktop\Proyecto-Final_Redes\Proyecto-final_Grupo-1_Redes_Sec-10"
Set-Location "$repo\infra\terraform"

terraform init
terraform fmt -check -recursive
terraform validate -no-color
terraform plan -no-color -out=tfplan
terraform show -no-color tfplan | Out-File -FilePath "$repo\evidence\deployment\terraform-plan.txt" -Encoding utf8
```

El plan esperado crea aproximadamente 20 recursos administrados: VPC, cinco subredes, dos tablas, cinco asociaciones, Internet Gateway, dos grupos de seguridad, llave y tres EC2. Debe indicar sólo adiciones; si propone modificar o destruir recursos no reconocidos, no aplicar.

El archivo `tfplan` es binario y no se versiona. `terraform-plan.txt` sí puede conservarse después de revisar que no contenga secretos.

## 9. Aplicar el prototipo

Aplicar únicamente después de revisar el plan y confirmar costos:

```powershell
terraform apply -no-color .\tfplan 2>&1 |
  Tee-Object -FilePath "$repo\evidence\deployment\terraform-apply.txt"
if ($LASTEXITCODE -ne 0) { throw "terraform apply falló; conservar el estado y revisar la salida." }

terraform output -json |
  Out-File -FilePath "$repo\evidence\deployment\terraform-outputs.json" -Encoding utf8
```

Aplicar un plan guardado ejecuta exactamente lo revisado. No usar `-auto-approve` ni recrear un plan distinto a último momento.

Obtener valores:

```powershell
$vpcId = terraform output -raw vpc_id
$bastionIp = terraform output -raw bastion_public_ip
$ventasIps = terraform output -json ventas_private_ips | ConvertFrom-Json

Write-Output "VPC: $vpcId"
Write-Output "Bastión: $bastionIp"
Write-Output "Ventas A: $($ventasIps[0])"
Write-Output "Ventas B: $($ventasIps[1])"
```

Esperar a que las tres instancias muestren estado `running` y comprobaciones `2/2 checks passed` en EC2. Si SSH todavía no responde, verificar los checks, la IP administrativa, la conectividad saliente `22/tcp` de la red local y el grupo del bastión. No abrir SSH al mundo como solución rápida.

## 10. Ejecutar la prueba real de ping

La prueba positiva entra a Ventas A mediante el bastión y ejecuta ping hacia Ventas B:

```powershell
& "$repo\scripts\test-connectivity.ps1" `
  -PrivateKey "$repo\tmp\rednova-fase1" `
  -BastionIp $bastionIp `
  -SourcePrivateIp $ventasIps[0] `
  -TargetPrivateIp $ventasIps[1]

Get-Content "$repo\evidence\connectivity\ping-private.txt"
```

Criterios obligatorios:

- origen y destino pertenecen a `10.10.0.64/26`;
- ambas IP son privadas;
- aparecen cuatro paquetes transmitidos y cuatro recibidos;
- la pérdida es `0%`;
- la evidencia registra fecha, origen, destino y bastión.

### Prueba negativa de aislamiento

Desde el bastión, ICMP hacia Ventas debe fallar porque el grupo de Ventas permite ICMP sólo entre sus propios miembros:

```powershell
$negative = & ssh -i "$repo\tmp\rednova-fase1" `
  -o StrictHostKeyChecking=accept-new `
  -o ConnectTimeout=20 `
  "ec2-user@$bastionIp" `
  "ping -c 4 $($ventasIps[0])" 2>&1
$negativeExit = $LASTEXITCODE
$negative | Set-Content -LiteralPath "$repo\evidence\connectivity\ping-bastion-negative.txt" -Encoding utf8
$negative

if ($negativeExit -eq 0) {
  throw "El ping desde el bastión tuvo éxito; revisar el grupo de seguridad de Ventas."
}
```

Un tiempo de espera desde el bastión es el resultado esperado. Un fallo SSH antes de ejecutar el ping no demuestra aislamiento y debe corregirse.

## 11. Capturas requeridas

Crear la carpeta de capturas y usar PNG:

```powershell
New-Item -ItemType Directory -Force -Path "$repo\evidence\screenshots" | Out-Null
```

Cada captura debe mostrar la región, nombre o identificador del recurso y suficiente contexto para entender qué demuestra. No debe contener claves, tokens, contraseñas, archivos de credenciales ni la llave privada.

| Archivo sugerido | Pantalla o terminal | Debe demostrar |
|---|---|---|
| `01-identidad-region.png` | `aws sts get-caller-identity` y región | Cuenta/rol autorizados; ocultar parcialmente el ID si se publicará |
| `02-terraform-plan.png` | Resumen del plan | Recursos previstos y ausencia de destrucciones inesperadas |
| `03-terraform-apply.png` | Final de `terraform apply` | `Apply complete` y conteo real |
| `04-vpc.png` | VPC Console, detalle de la VPC | Nombre, VPC ID, `10.10.0.0/24`, estado y región |
| `05-subredes.png` | Subnets filtradas por VPC | Cinco nombres, cinco CIDR y zona de disponibilidad |
| `06-tabla-publica.png` | Route table pública | Ruta local, `0.0.0.0/0 -> igw-*`, asociaciones de Visitas y Administración |
| `07-tabla-privada.png` | Route table privada | Sólo ruta local y asociaciones de Ventas, TI y Data Center |
| `08-sg-bastion.png` | Inbound rules del SG del bastión | SSH sólo desde `admin_cidr /32` |
| `09-sg-ventas.png` | Inbound rules del SG de Ventas | SSH desde SG del bastión e ICMP self-reference |
| `10-instancias.png` | EC2 Instances filtradas por proyecto | Bastión y dos Ventas, estado `running`, subredes e IP; sólo bastión con IP pública |
| `11-outputs.png` | `terraform output` | VPC ID, IP pública del bastión y dos IP privadas |
| `12-ping-privado.png` | PowerShell mostrando `ping-private.txt` | Origen, destino y `0% packet loss` |
| `13-aislamiento.png` | Prueba negativa desde el bastión | ICMP rechazado por la política prevista |
| `14-destroy.png` | Aplicación del plan de destrucción | `Destroy complete` y conteo destruido |
| `15-auditoria-final-aws.png` | Consola filtrada o comandos AWS | No quedan VPC ni instancias activas del proyecto |

Recomendaciones para las capturas:

- incluir el reloj o registrar una marca de tiempo en la evidencia textual;
- mantener visibles región, filtros y columnas relevantes;
- recortar menús vacíos, no los campos probatorios;
- ocultar únicamente información sensible o irrelevante;
- no editar valores, estados, direcciones o resultados;
- redactar un pie en el informe que explique qué prueba cada imagen.

## 12. Destruir y verificar

No cerrar la sesión ni el laboratorio antes de destruir. Crear y revisar un plan de destrucción:

```powershell
Set-Location "$repo\infra\terraform"

terraform plan -destroy -no-color -out=destroy.tfplan
terraform show -no-color destroy.tfplan |
  Out-File -FilePath "$repo\evidence\deployment\destroy-plan.txt" -Encoding utf8

terraform apply -no-color .\destroy.tfplan 2>&1 |
  Tee-Object -FilePath "$repo\evidence\deployment\destroy.txt"
if ($LASTEXITCODE -ne 0) { throw "La destrucción falló; no cerrar la sesión hasta resolverla." }

terraform state list
```

`terraform state list` debe quedar sin salida. Después verificar en AWS Console que no haya recursos activos con la etiqueta `Project=CC3067-Fase-1`.

Comprobaciones de apoyo:

```powershell
aws ec2 describe-vpcs `
  --filters Name=tag:Project,Values=CC3067-Fase-1 `
  --query 'Vpcs[].{VpcId:VpcId,State:State}' --output table

aws ec2 describe-instances `
  --filters Name=tag:Project,Values=CC3067-Fase-1 Name=instance-state-name,Values=pending,running,stopping,stopped `
  --query 'Reservations[].Instances[].{Id:InstanceId,State:State.Name,Name:Tags[?Key==`Name`]|[0].Value}' --output table

aws ec2 describe-internet-gateways `
  --filters Name=tag:Project,Values=CC3067-Fase-1 `
  --query 'InternetGateways[].InternetGatewayId' --output table
```

Una instancia terminada puede seguir visible temporalmente en EC2, pero no debe quedar en `pending`, `running`, `stopping` o `stopped`. Revisar también volúmenes, interfaces, grupos de seguridad, llave EC2 e Internet Gateway. No borrar `terraform.tfstate` hasta confirmar la destrucción.

Si el `apply` falla a mitad:

1. conservar el estado;
2. renovar credenciales si expiraron;
3. ejecutar `terraform state list`;
4. revisar `terraform plan`;
5. corregir la causa o destruir lo creado;
6. confirmar en AWS que no quedan recursos facturables.

## 13. Incorporar la evidencia al informe

Después de una ejecución exitosa, el siguiente agente debe:

1. copiar únicamente las capturas seleccionadas y redactadas a `docs/fase-1/assets/screenshots/`;
2. mantener las secciones 8.7 y 8.8 eliminadas, como solicitó el usuario;
3. incorporar las capturas dentro de las secciones existentes 8.3-8.6, 9.4-9.7 y 11.4, sin crear títulos eliminados;
4. cambiar P-03, P-04, P-05 y P-06 de pendiente a verificado sólo si existe evidencia real;
5. sustituir el diagnóstico `No valid credential sources found` por el resultado observado;
6. incluir IDs, IP privadas, región, fecha y conteos reales sin publicar secretos;
7. actualizar conclusiones y `docs/fase-1/AUDITORIA_FINAL.md`;
8. recompilar con `scripts/build-report.ps1`;
9. renderizar e inspeccionar visualmente todas las páginas;
10. escanear secretos y archivos sensibles antes de Git;
11. hacer commit y push sólo si el usuario lo autoriza.

Archivos que nunca deben llegar a Git:

- `terraform.tfvars`;
- `terraform.tfstate` y copias;
- `tfplan` y `destroy.tfplan`;
- llaves privadas o públicas temporales;
- `.aws/credentials`;
- variables de entorno copiadas a texto;
- capturas que muestren secretos o tokens.

## 14. Criterio de terminado

La fase queda experimentalmente completa cuando se cumplen todos estos puntos:

- `terraform apply` terminó en la cuenta y región aprobadas;
- las cinco subredes y sus rutas coinciden con el plan;
- existen exactamente un bastión y dos instancias privadas de Ventas durante la prueba;
- el ping Ventas A -> Ventas B reporta `0%` de pérdida;
- el ping bastión -> Ventas falla por aislamiento y no por un error SSH;
- las capturas y salidas se guardaron sin secretos;
- `terraform destroy` terminó correctamente;
- no quedan recursos activos o facturables del proyecto;
- el PDF fue actualizado, recompilado y revisado página por página;
- la auditoría dejó de marcar los tres requisitos cloud como pendientes.

## 15. Referencias operativas oficiales

- [Instalar AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [Configurar AWS CLI con IAM Identity Center](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)
- [Configuración y archivos de credenciales de AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- [`aws sts get-caller-identity`](https://docs.aws.amazon.com/cli/latest/reference/sts/get-caller-identity.html)
- [`terraform plan`](https://developer.hashicorp.com/terraform/cli/commands/plan)
- [`terraform apply`](https://developer.hashicorp.com/terraform/cli/commands/apply)
- [`terraform destroy`](https://developer.hashicorp.com/terraform/cli/commands/destroy)

## 16. Regla final

Si no hay credenciales autorizadas, presupuesto confirmado o una ruta clara para destruir, no se debe desplegar. En ese caso se conserva el estado actual como diseño validado localmente y se reporta el bloqueo de forma explícita.
