# Infraestructura de la Fase 1

La configuración crea una VPC `10.10.0.0/24`, cinco subredes, tablas de rutas pública/privada, un Internet Gateway y grupos de seguridad. El cómputo está deshabilitado por defecto para evitar cargos accidentales.

## Uso resumido

1. Copie `terraform.tfvars.example` como `terraform.tfvars`.
2. Sustituya `admin_cidr` por su IP pública con `/32`.
3. Genere una llave SSH temporal fuera del control de versiones.
4. Ejecute `terraform init`, `terraform fmt -check`, `terraform validate` y `terraform plan`.
5. Use `terraform apply` sólo durante la ventana de prueba.
6. Capture evidencias y ejecute `terraform destroy`.

No publique `terraform.tfvars`, estados, archivos `.pem`, llaves privadas ni credenciales AWS.
