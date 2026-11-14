# Entrega final acumulativa

Esta carpeta contiene la documentación de integración de Fase 1 y Fase 2. El PDF final de
Fase 1 en `output/pdf/` se conserva sin modificaciones.

## Estado del bloque de Pablo

Implementado localmente:

- DMZ `10.10.0.192/27`.
- Reserva futura `10.10.0.224/27`.
- Tabla de rutas pública dedicada a la DMZ.
- NACL de Visitas, TI y DMZ.
- Security Groups base de los servicios de Fase 2.
- Variables y outputs de integración.
- Diagrama lógico y matriz de flujos.
- Validador local del direccionamiento y reglas estructurales.

Pendiente de otros bloques:

- DNS e intranet: Andrés.
- Web pública, dominio y hardening: Roberto.
- Clientes de Visitas/TI, pruebas y evidencias: Genser.
- Despliegue, capturas y resultados reales: ventana AWS autorizada.

## Archivos

- `arquitectura-fase2.md`: diagrama y decisiones de red.
- `assets/diagrams/arquitectura-fase2.pdf`: diagrama vectorial para el informe.
- `assets/diagrams/arquitectura-fase2.png`: vista para revisión y presentación.
- `secciones/`: capítulos del reporte acumulativo; se crearán durante la integración final.
- `assets/`: diagramas renderizados y capturas redactadas.

Los diagramas se regeneran con `python scripts/generate-phase2-figures.py`.

## Regla de cierre

Un `terraform plan` no demuestra que la infraestructura exista. El reporte solo debe marcar un
requisito como verificado cuando exista salida real de la prueba y su evidencia correspondiente.
