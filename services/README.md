# Servicios de Data Center: DNS interno e intranet de RR. HH.

La web pública de Roberto se documenta por separado en
[`public-web/README.md`](public-web/README.md).

**Responsable:** Andrés Rafael Chivalán · **Rama integrada:** `Andrés` (incluye `fase-2-pablo`)

| Servicio | Host | IP | Puerto | Permitido desde |
|---|---|---|---|---|
| DNS interno (BIND9) | `ns1.rednova.internal` | `10.10.0.164` | UDP/TCP 53 | Ventas, TI, Data Center, Administración |
| Intranet RR. HH. (Nginx) | `rrhh.rednova.internal` | `10.10.0.165` | TCP 80 | Ventas, TI, Data Center, Administración |
| Administración de ambos | — | — | TCP 22 | Solo bastión |

Visitas, DMZ e Internet no tienen acceso a ninguno de los dos.

## Archivos

```text
services/dns/
  named.conf               /etc/named.conf (ACL, recursión limitada, reenvío a 10.10.0.2, logs)
  db.rednova.internal      zona directa: ns1, dns, rrhh, intranet, ti-cliente, web-dmz
  db.10.10.0               zona inversa (PTR)
  rednova-internal.conf    drop-in de systemd-resolved para clientes (split DNS)
  configure-dns-client.sh  instala el drop-in en un cliente interno
  dnsquery.py              sustituto de dig sin dependencias (los clientes no tienen bind-utils)
services/intranet/
  index.html               página estática de RR. HH. sin recursos externos
  nginx.conf               /etc/nginx/nginx.conf (allow/deny, cabeceras, server_tokens off)
infra/terraform/
  services.tf              EC2 dns e intranet (Data Center, sin IP pública, IMDSv2, EBS cifrado)
  endpoints.tf             VPC Gateway Endpoint de S3 para que dnf funcione sin NAT
  templates/dns-user-data.tftpl, templates/intranet-user-data.tftpl
  phase2-security.tf       (cambio) salida 443 de los SG dns/intranet hacia el prefijo S3
scripts/validate-andres-phase2.py   validación local -> evidence/fase-2/dns/andres-validation.txt
```

## Decisiones de diseño

- **Instalación sin NAT.** Data Center es privada. Los repositorios de Amazon Linux 2023 están
  en buckets S3 de AWS, así que un *Gateway Endpoint* de S3 asociado a la tabla privada permite
  `dnf install bind nginx` sin Internet y sin costo. Su política solo permite leer
  `al2023-repos-<región>-de612dc2`. Se crea únicamente con `enable_phase2_compute = true`.
- **DNS dividido.** No se cambia el DHCP Options Set de la VPC: Visitas y DMZ deben seguir
  usando `10.10.0.2`. Los clientes internos envían solo `*.rednova.internal` a BIND9 mediante un
  drop-in de `systemd-resolved`. BIND9 reenvía cualquier otro nombre a `10.10.0.2`.
- **Defensa en profundidad.** Security Group (principal) + ACL `redes_autorizadas` en BIND9 +
  `allow/deny` en Nginx con las mismas cuatro redes. La red de Data Center usa la NACL por
  defecto de la VPC; los bloqueos de Visitas y DMZ ya ocurren en sus propias NACL.
- **Configuración versionada.** Terraform incrusta los archivos en base64 dentro del
  `user_data`; cambiar un archivo reemplaza la instancia (`user_data_replace_on_change`).
- **Precondiciones.** El `plan` falla si alguien cambia las IP `10.10.0.164/165` o el dominio
  sin actualizar las zonas, o si se activa Fase 2 sin `enable_compute` (llave y bastión).

## Validación local (antes de la ventana)

```powershell
python scripts/validate-andres-phase2.py
cd infra/terraform
terraform init -backend=false
terraform fmt -check -recursive
terraform validate
```

`named-checkconf`, `named-checkzone` y `nginx -t` se ejecutan si están instalados (WSL/Linux) y
siempre se ejecutan dentro del `user_data`.

## Procedimiento en la ventana AWS

En `terraform.tfvars`: `enable_compute = true`, `enable_phase2_compute = true`, `admin_cidr`
con su `/32` y `public_key_path`. Después del `apply` aprobado:

```powershell
terraform output datacenter_services
terraform output bastion_public_ip
terraform output ventas_private_ips
```

Abra un túnel SSH con agente (la llave nunca se copia al bastión):

```powershell
ssh-add <llave-temporal>
$B = "ec2-user@<bastion_public_ip>"
```

### 1. Verificar que los servicios arrancaron (2-4 min después del apply)

```bash
ssh -A $B
ssh ec2-user@10.10.0.164 'sudo tail -5 /var/log/rednova-dns-setup.log; systemctl is-active named; sudo ss -lnup | grep :53'
ssh ec2-user@10.10.0.165 'sudo tail -5 /var/log/rednova-intranet-setup.log; systemctl is-active nginx'
```

Debe verse `DNS interno listo`, `Intranet lista`, `active` y `HTTP local: 200`.

### 2. Copiar las herramientas de prueba a un cliente de Ventas

`<IP_VENTAS>` es una de las IP de `terraform output ventas_private_ips`. Repita la copia en el
cliente de TI y en el bastión para F2-03 y F2-04.

```powershell
scp -J $B services/dns/dnsquery.py services/dns/configure-dns-client.sh ec2-user@<IP_VENTAS>:
```

### 3. Pruebas F2-01 a F2-04

Guarde cada salida completa en `evidence/fase-2/dns/` y tome la captura indicada.

| ID | Origen | Comando | Esperado | Evidencia |
|---|---|---|---|---|
| F2-01 | Ventas `<IP_VENTAS>` | `python3 dnsquery.py rrhh.rednova.internal` | `A 10.10.0.165`, `autoritativa=si` | `f2-01-dns-ventas.txt`, `07-dns-interno-exitoso.png` |
| F2-01b | Ventas | `sudo bash configure-dns-client.sh` y `resolvectl query rrhh.rednova.internal` | `10.10.0.165` | mismo archivo |
| F2-02 | Ventas | `curl -s -o /dev/null -w '%{http_code}\n' http://rrhh.rednova.internal/` | `200` | `f2-02-intranet-ventas.txt`, `08-intranet-interna-exitosa.png` |
| F2-03 | TI `10.10.0.132` | los mismos dos comandos | `10.10.0.165` y `200` | `f2-03-intranet-ti.txt` |
| F2-04 | Bastión (Administración) | los mismos dos comandos | `10.10.0.165` y `200` | `f2-04-intranet-admin.txt` |

Para registrar fecha, origen y comando en el archivo:

```bash
{ date -Is; hostname -I; echo '$ curl http://rrhh.rednova.internal/'; \
  curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://rrhh.rednova.internal/; } | tee f2-02.txt
```

Para la captura de la página, use un túnel desde su PC y abra `http://localhost:8080`:

```powershell
ssh -J $B -L 8080:10.10.0.165:80 ec2-user@<IP_VENTAS>
```

El túnel termina en Ventas, por lo que el origen visto por la intranet es la IP de Ventas.

### 4. Evidencia del lado servidor

```bash
ssh ec2-user@10.10.0.164 'sudo tail -20 /var/named/data/queries.log'   # IP de cada cliente
ssh ec2-user@10.10.0.165 'sudo tail -20 /var/log/nginx/access.log'     # 200 desde Ventas, TI y bastión
```

### 5. Apoyo a las pruebas negativas de Pablo y Andrés Rafael (F2-05/F2-06)

Desde el cliente de Visitas (`10.10.0.4`), copiando `dnsquery.py`:

```bash
curl -m 5 -s -o /dev/null -w '%{http_code}\n' http://10.10.0.165/   # 000 = tiempo agotado
python3 dnsquery.py rrhh.rednova.internal 10.10.0.164               # tiempo agotado
```

Desde Internet: la intranet no tiene IP pública ni registro DNS público, por lo que no existe
ruta para alcanzarla.

## Si algo falla

| Síntoma | Revisar |
|---|---|
| `dnf` agota el tiempo en el log de arranque | Endpoint S3 asociado a la tabla privada; salida 443 al prefijo S3 en el SG; región correcta en la política |
| `dnf` responde 403 | Nombre del bucket en `endpoints.tf` (`al2023-repos-<región>-de612dc2`) |
| `named` no inicia | `sudo journalctl -u named`, `sudo named-checkconf -z /etc/named.conf` |
| `status=REFUSED` | El origen no está en `redes_autorizadas` |
| `curl` devuelve `403` | El origen no está en los `allow` de Nginx |
| `curl` devuelve `000` desde una red autorizada | Security Group o NACL; probar `curl http://10.10.0.165/` para descartar DNS |
| El nombre no resuelve pero `dnsquery.py` sí | Falta `configure-dns-client.sh` en ese cliente |

Registros completos: `/var/log/cloud-init-output.log` en cada instancia.
