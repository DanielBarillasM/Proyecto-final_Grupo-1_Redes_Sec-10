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

Las instancias de DNS e intranet de Andrés están integradas en `services.tf`; la web pública de
Roberto está integrada en `public-web.tf`. Los clientes temporales de Visitas (`10.10.0.4`, con
IPv4 pública efímera) y TI (`10.10.0.132`, privado) de Genser están en `test-clients.tf`.
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

- TI inicia ICMP hacia todas las subredes. Para que la respuesta vuelva, los SG de Ventas,
  bastión, DNS, intranet y web aceptan ICMP echo desde `10.10.0.128/27`, y las NACL de Visitas
  y DMZ (salida) y de TI (entrada) admiten únicamente el ICMP echo-reply (tipo 0). Un
  echo-request iniciado hacia TI sigue cayendo en la regla 200 de la NACL de TI.

## Estado de integración

Los cuatro bloques están integrados. `python scripts/validate-phase2.py` evalúa la matriz de
tráfico completa contra los SG y NACL declarados. No se debe ejecutar `apply` sin auditar el
estado real de AWS y obtener autorización de Andrés Rafael Chivalán.

No publique `terraform.tfvars`, estados, planes guardados, archivos `.pem`, llaves privadas ni
credenciales AWS.
