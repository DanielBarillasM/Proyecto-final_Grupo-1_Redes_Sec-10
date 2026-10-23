# Evidencias de la Fase 1

Esta carpeta conserva resultados reales o reproducibles. No contiene credenciales,
llaves privadas ni el estado de Terraform.

## Despliegue

- `deployment/cidr-validation.txt`: capacidad, contención, canonicidad y no solapamiento.
- `deployment/terraform-validate.txt`: validación local de Terraform.
- `deployment/terraform-plan.txt`: plan generado contra AWS.
- `deployment/terraform-apply.txt`: ejecución real; confirma 20 recursos creados.
- `deployment/terraform-outputs.json`: VPC, subredes e IP privadas observadas.

## Conectividad

- `connectivity/ping-private.txt`: ping real entre `10.10.0.71` y `10.10.0.79`, con 0 % de pérdida.
- `connectivity/ping-bastion-negative.txt`: intento desde el bastión, con 100 % de pérdida.

## Capturas renombradas

- `screenshots/01-aws-vpc-creada-disponible.png`: VPC `rednova-fase1-vpc` en estado disponible.
- `screenshots/02-aws-cinco-subredes-segmentadas.png`: mapa de las cinco subredes.
- `screenshots/03-aws-tablas-rutas-e-internet-gateway.png`: tablas pública/privada e Internet Gateway.
- `screenshots/04-prueba-icmp-bastion-bloqueada.png`: prueba negativa ICMP desde el bastión.

## Cierre operativo

Las pruebas P-01 a P-05 cubren el alcance técnico documentado para la Fase 1 y
quedaron verificadas. Después de cada ventana temporal, el equipo debe revisar
la consola de AWS y retirar los recursos que ya no sean necesarios para evitar
cargos residuales.
