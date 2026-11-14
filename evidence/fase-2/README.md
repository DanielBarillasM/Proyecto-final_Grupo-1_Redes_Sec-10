# Evidencias de Fase 2

Esta carpeta separa validaciones locales reproducibles de evidencias obtenidas en AWS.

## Disponibles en el bloque de Pablo

- `deployment/pablo-validation.txt`: CIDR, reserva, IP propuestas y comprobaciones
  estructurales.
- `deployment/terraform-fmt.txt`: formato recursivo de Terraform.
- `deployment/terraform-validate.txt`: validación con Terraform 1.17.2 y AWS Provider 6.73.0.

## Pendientes de una ventana AWS autorizada

- `terraform-plan.txt` y plan revisado.
- `terraform-apply.txt`.
- Outputs reales sin secretos.
- Capturas de DMZ, rutas, NACL y Security Groups.
- Pruebas de DNS, intranet, Visitas, TI y web pública.
- Auditoría de recursos y cierre de costos.

Un archivo de plan guardado, un estado, `.tfvars`, claves o credenciales no deben almacenarse
en Git.
