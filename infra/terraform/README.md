# Infraestructura acumulativa de Fase 1 y Fase 2

La configuración conserva la VPC `10.10.0.0/24` y las cinco subredes de Fase 1. La Fase 2
divide la reserva `10.10.0.192/26` en una DMZ `10.10.0.192/27` y una nueva reserva
`10.10.0.224/27`.

El bloque de Pablo agrega:

- DMZ pública con tabla de rutas dedicada al Internet Gateway.
- NACL administradas para Visitas, TI y DMZ.
- Security Groups base para Visitas, TI, DNS, intranet y web pública.
- Variables de dominio, IP privadas, HTTPS y control de cómputo.
- Outputs de DMZ, reserva, dominios, IP y NACL.

Las instancias y servicios de Fase 2 se integrarán en archivos separados por sus responsables.
`enable_compute` y `enable_phase2_compute` permanecen en `false` por defecto.

## Uso resumido

1. Audite primero los recursos de Fase 1 y recupere o importe su estado si todavía existen.
2. Copie `terraform.tfvars.example` como `terraform.tfvars`.
3. Sustituya `admin_cidr` por su IP pública con `/32`.
4. Configure el dominio público real o deje `public_domain = ""` durante la validación local.
5. Genere una llave SSH temporal fuera del control de versiones si habilitará cómputo.
6. Ejecute `terraform init -backend=false`, `terraform fmt -check -recursive` y
   `terraform validate`.
7. Genere y revise `terraform plan`; no aplique desde una copia sin estado.
8. Use `terraform apply` solo durante una ventana autorizada y sobre un plan guardado.
9. Capture evidencias, audite costos y retire los recursos temporales.

## Decisiones de red

- Los Security Groups funcionan como firewall stateful por instancia.
- Las NACL agregan control stateless por subred; sus reglas de retorno usan puertos
  `1024-65535`.
- Visitas permite DNS al resolvedor `10.10.0.2` y HTTP/HTTPS a Internet, pero bloquea el resto
  de la VPC. Su cliente de prueba necesitará una IPv4 pública temporal porque
  `map_public_ip_on_launch` permanece deshabilitado.
- TI no acepta conexiones laterales; únicamente SSH desde el bastión. Sus respuestas quedan
  permitidas por el comportamiento stateful del Security Group y los puertos efímeros de la
  NACL.
- La DMZ permite HTTP público, HTTPS cuando se habilite y SSH solo desde el bastión. Su NACL
  bloquea conexiones iniciadas hacia la red interna antes de evaluar las salidas a Internet.

## Dependencias todavía no integradas

- EC2 y `user_data` de DNS e intranet: Andrés.
- EC2, Elastic IP, Nginx, dominio y HTTPS: Roberto.
- Clientes EC2 de Visitas/TI y pruebas automáticas: Genser.

No se debe ejecutar `apply` hasta integrar y revisar estos componentes.

No publique `terraform.tfvars`, estados, planes guardados, archivos `.pem`, llaves privadas ni
credenciales AWS.
