# Evidencias de Fase 2

Esta carpeta separa validaciones locales reproducibles de evidencias obtenidas en AWS.

## Disponibles en la integración de Pablo, Andrés y Roberto

- `deployment/pablo-validation.txt`: CIDR, reserva, IP propuestas y comprobaciones
  estructurales.
- `deployment/terraform-fmt.txt`: formato recursivo de Terraform.
- `deployment/terraform-validate.txt`: validación con Terraform 1.17.2 y AWS Provider 6.73.0.
- `dns/andres-validation.txt`: coherencia local de BIND9, zonas, Nginx, Terraform y controles
  de acceso; distingue explícitamente las pruebas nativas omitidas por falta de herramientas.
- `public-web/roberto-validation.txt`: coherencia de EC2, Elastic IP, Nginx, hardening,
  `user_data`, scripts y controles de red; distingue las pruebas nativas omitidas.

- `connectivity/genser-validation.txt`: clientes de Visitas/TI, plantilla `user_data`, script de
  pruebas y matriz estática de 50 flujos evaluada contra los SG y NACL de Terraform.

## Generadas por `scripts/test-phase2.ps1` durante la ventana

Pablo Daniel Barillas Moreno y Andrés Rafael Chivalán ejecutan la suite y recopilan estas
evidencias. Genser Andree Catalán Espina conserva la autoría de los clientes y la automatización.

- `pruebas-fase2.txt` y `pruebas-fase2.csv`: matriz con fecha, commit, autorización, origen,
  destino, esperado, obtenido y veredicto.
- `connectivity/F2-0x*.txt`, `security/F2-06|11|12*.txt`, `dns/F2-01|02|04.txt` y
  `public-web/F2-10|13*.txt`: una evidencia de texto por prueba, con la salida redactada.

## Pendientes de una ventana AWS autorizada

- `terraform-plan.txt` y plan revisado.
- `terraform-apply.txt`.
- Outputs reales sin secretos.
- Capturas de DMZ, rutas, NACL y Security Groups.
- Pruebas de DNS, intranet, Visitas, TI y web pública.
- Auditoría de recursos y cierre de costos.

Un archivo de plan guardado, un estado, `.tfvars`, claves o credenciales no deben almacenarse
en Git.
