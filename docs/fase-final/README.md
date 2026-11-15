# Entrega final acumulativa

Esta carpeta contiene la documentación de integración de Fase 1 y Fase 2. El PDF final de
Fase 1 en `output/pdf/` se conserva sin modificaciones.

## Estado integrado de Pablo, Andrés, Roberto y Genser

Implementado localmente:

- DMZ `10.10.0.192/27`.
- Reserva futura `10.10.0.224/27`.
- Tabla de rutas pública dedicada a la DMZ.
- NACL de Visitas, TI y DMZ.
- Security Groups base de los servicios de Fase 2.
- Variables y outputs de integración.
- Diagrama lógico y matriz de flujos.
- Validador local del direccionamiento y reglas estructurales.
- DNS interno BIND9 en Data Center y zonas directa/inversa.
- Intranet privada de RR. HH. con Nginx y HTML estático.
- EC2 privadas, `user_data` y endpoint Gateway de S3 para instalar paquetes sin NAT.
- Validador local de coherencia entre DNS, Nginx, Terraform y controles de acceso.
- Web pública de Ventas en la DMZ con EC2, Elastic IP temporal y Nginx.
- `user_data`, hardening por capas, validador local y procedimiento de HTTPS opcional.

- Clientes temporales de Visitas y TI, sonda remota, suite `test-phase2.ps1` y validador con
  matriz estática de tráfico (Genser).

Pendiente:

- Despliegue, ejecución de la suite, capturas y resultados reales: ventana AWS autorizada.

## Archivos

- `arquitectura-fase2.md`: diagrama y decisiones de red.
- `assets/diagrams/arquitectura-fase2.pdf`: diagrama vectorial para el informe.
- `assets/diagrams/arquitectura-fase2.png`: vista para revisión y presentación.
- `sections/`: capítulos del reporte acumulativo; se completarán durante la integración final.
- `assets/`: diagramas renderizados y capturas redactadas.

Los diagramas se regeneran con `python scripts/generate-phase2-figures.py`.

## Regla de cierre

Un `terraform plan` no demuestra que la infraestructura exista. El reporte solo debe marcar un
requisito como verificado cuando exista salida real de la prueba y su evidencia correspondiente.
