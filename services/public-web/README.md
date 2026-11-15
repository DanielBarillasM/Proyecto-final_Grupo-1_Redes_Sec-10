# Web pública de Ventas

**Responsable:** Roberto Emiliano Otoniel Camposeco Torres
**Rama integrada:** `Roberto-Fasedos` (incluye los bloques de Pablo y Andrés)

La web usa la IP privada `10.10.0.196` en la DMZ `10.10.0.192/27`, el Security Group
`public_web` y una Elastic IP temporal. HTTP es obligatorio; HTTPS es opcional y solo se activa
cuando el dominio público ya resuelve a la Elastic IP.

## Archivos

- `index.html`: página estática de Ventas sin dependencias externas.
- `nginx.conf`: servidor público HTTP con cabeceras y límites por IP.
- `enable-https.sh`: instalación manual de Certbot y redirección a HTTPS.
- `../hardening/hardening.sh`: SSH, `sysctl`, servicios y `nftables`.
- `../../infra/terraform/public-web.tf`: EC2, Elastic IP y outputs.
- `../../infra/terraform/templates/public-web-user-data.tftpl`: instalación inicial.

## Validación local

```powershell
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform validate
python scripts/validate-pablo-phase2.py
python scripts/validate-andres-phase2.py
python scripts/validate-roberto-phase2.py
```

## Regla previa a AWS

Antes de usar AWS CLI, consola, `terraform plan`, `apply`, DNS público, Elastic IP, pruebas o
`destroy`, Roberto o Genser deben solicitar a Andrés Rafael Chivalán la cuenta, región,
rol/perfil temporal, estado Terraform, ventana y alcance autorizados. No se comparten claves,
tokens, `.tfvars`, estados ni llaves privadas por Git o chat.

## Ventana AWS autorizada

1. Confirmar con Andrés que la identidad, región y estado son los correctos.
2. Revisar y aprobar el plan antes de aplicar.
3. Obtener `public_web.public_ip` y `public_dns_record` desde los outputs.
4. Crear el registro A público solo con autorización específica.
5. Esperar que `/var/log/rednova-public-web-setup.log` termine en `Web pública lista`.
6. Ejecutar F2-10, F2-11 y F2-12 y conservar salida de texto y capturas.
7. Auditar y retirar la Elastic IP y EC2 durante la ventana de cierre aprobada.

## Verificación por bastión

```powershell
$B = "ec2-user@<bastion_public_ip>"
ssh -J $B ec2-user@10.10.0.196 `
  'sudo tail -30 /var/log/rednova-public-web-setup.log; systemctl is-active nginx nftables'
```

## HTTPS opcional

Primero configure `enable_https = true`, revise/aplique el plan autorizado y confirme que el
dominio resuelve a la Elastic IP. Después copie el script por el bastión:

```powershell
scp -J $B services/public-web/enable-https.sh ec2-user@10.10.0.196:
ssh -J $B ec2-user@10.10.0.196
```

En la EC2:

```bash
sudo ./enable-https.sh <dominio-publico> <correo-contacto>
```

La prueba F2-13 exige certificado válido y redirección HTTP a HTTPS. Si HTTPS no fue aprobado,
se mantiene `enable_https = false` y F2-13 se documenta como opcional no ejecutada.
