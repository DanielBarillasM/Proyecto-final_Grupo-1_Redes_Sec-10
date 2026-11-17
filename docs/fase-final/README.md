# Entrega final acumulativa

Esta carpeta contiene la documentación acumulativa de Fase 1 y Fase 2. El documento maestro
`main.tex` genera `output/pdf/Proyecto_Final_Fases_1_y_2_Grupo_1.pdf`; el PDF histórico de Fase 1
se conserva como antecedente.

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
  matriz estática de tráfico (implementación de Genser; ejecución y evidencia a cargo de Andrés
  Rafael; revisión documental de Pablo).

Verificado en AWS:

- Plan de 41 recursos, despliegue temporal, 36 resultados correctos y 3 omisiones documentadas.
- DNS, intranet, aislamiento de Visitas, política de TI, web por IP, puertos y cierre de recursos.

Pendiente de entrega: captura dedicada de la web pública, carné de Genser y decisión sobre el
dominio/HTTPS opcional.

## Archivos

- `arquitectura-fase2.md`: diagrama y decisiones de red.
- `assets/diagrams/arquitectura-fase2.pdf`: diagrama vectorial para el informe.
- `assets/diagrams/arquitectura-fase2.png`: vista para revisión y presentación.
- `main.tex` y `preamble.tex`: documento maestro acumulativo y estilo compartido.
- `sections/`: capítulos integrados del reporte acumulativo.
- `assets/`: diagramas renderizados y capturas redactadas.
- `presentacion.html`: presentación autónoma de doce diapositivas.
- `guion-presentacion.tex`: distribución y notas de exposición.
- `aportes-integrantes.docx`: resumen editable de aportes y responsabilidades.

La compilación reproducible se ejecuta con `pwsh scripts/build-final-report.ps1`.

Los diagramas se regeneran con `python scripts/generate-phase2-figures.py`.

## Regla de cierre

Un `terraform plan` no demuestra que la infraestructura exista. El reporte marca cada requisito
como verificado únicamente cuando existe salida real de la prueba y evidencia correspondiente.
