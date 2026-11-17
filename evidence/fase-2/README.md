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

Andrés Rafael Chivalán ejecutó la ventana y recopiló las capturas; Pablo Daniel Barillas Moreno
revisó e integró el material. Genser Andree Catalán Espina conserva la autoría de los clientes y la
automatización. La etiqueta `Pablo/Andrés Rafael` de las salidas se conserva como registro histórico
de la versión de la suite utilizada.

- `pruebas-fase2.txt` y `pruebas-fase2.csv`: matriz con fecha, commit, autorización, origen,
  destino, esperado, obtenido y veredicto.
- `connectivity/F2-0x*.txt`, `security/F2-06|11|12*.txt`, `dns/F2-01|02|04.txt` y
  `public-web/F2-10|13*.txt`: una evidencia de texto por prueba, con la salida redactada.

## Capturas organizadas

Las capturas verificadas se encuentran en `screenshots/`, con nombres correlativos y descriptivos.
Documentan el plan, los outputs del despliegue, la identidad operativa, el inventario posterior al
cierre, DNS, intranet, Visitas, TI, el resumen de la suite, `nftables` y la página pública cargada
mediante la Elastic IP temporal (`13-web-publica-elastic-ip.jpeg`).

## Pendientes antes de la entrega

- HTTPS y F2-13a/F2-13b, únicamente si se activa el punto opcional.

Un archivo de plan guardado, un estado, `.tfvars`, claves o credenciales no deben almacenarse
en Git.
