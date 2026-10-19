# Auditoría final — Fase 1

## Alcance

Esta auditoría contrasta el informe compilado, sus fuentes LaTeX, los cálculos de direccionamiento, el prototipo Terraform y las evidencias disponibles con los requisitos de la Fase 1. Distingue expresamente entre resultados reproducibles localmente y pruebas que sólo pueden cerrarse mediante una ejecución autorizada en AWS.

## Resultado documental

- PDF compilado: `output/pdf/Proyecto_Final_Fase_1_Grupo_1.pdf`.
- Extensión revisada: 45 páginas.
- Título del capítulo inicial corregido a **Resumen**.
- Eliminada la observación administrativa solicitada.
- Corregido el bloque **Resultado principal** para evitar traslapes.
- La sección 8.6 ahora se titula **Comandos de ejecución previstos**.
- Eliminadas las secciones 8.7 y 8.8 anteriores.
- La evidencia local se presenta mediante una terminal de PowerShell de Windows.
- Eliminado el capítulo D, **Lista final de revisión**.
- Diagramas, tablas y figuras conservan numeración, pies y referencias internas.

## Validaciones locales

| Control | Estado | Evidencia |
|---|---|---|
| Compilación LaTeX | Verificado | PDF generado sin errores relevantes de composición |
| Inspección visual | Verificado | Revisión página por página del PDF de 45 páginas |
| Cálculo CIDR | Verificado | Script y evidencia almacenados en `evidence/deployment/` |
| Solapamiento de subredes | Verificado | Los cinco bloques son canónicos, suficientes y no se solapan |
| Formato Terraform | Verificado | `terraform fmt -check -recursive` |
| Sintaxis Terraform | Verificado localmente | `terraform validate` con proveedor inicializado |
| Script de conectividad | Verificado estáticamente | Sintaxis PowerShell correcta; aún requiere instancias reales |
| Revisión de secretos | Verificado | No se detectaron credenciales ni llaves privadas versionadas |

## Trazabilidad de requisitos

| Identificador | Requisito | Estado final |
|---|---|---|
| P-01 | Planificar la VPC y cinco subredes | Verificado documentalmente |
| P-02 | Presentar cálculos explícitos de direccionamiento | Verificado |
| P-03 | Implementar el prototipo en una cuenta de nube | Pendiente externo |
| P-04 | Incluir capturas reales de VPC, EC2, rutas y seguridad | Pendiente externo |
| P-05 | Demostrar ping entre dos instancias privadas | Pendiente externo |
| P-06 | Registrar destrucción y ausencia de recursos residuales | Pendiente externo |
| P-07 | Entregar infraestructura como código reproducible | Verificado localmente |
| P-08 | Entregar informe ordenado, explícito y visual | Verificado |

## Pendientes externos

| Actividad | Situación comprobada | Estado |
|---|---|---|
| Implementar el prototipo en una cuenta de nube | Terraform está preparado y validado localmente, pero no existe evidencia de `apply` en AWS | Pendiente externo |
| Incluir capturas reales de la implementación cloud | Sólo existe evidencia local reproducible; no hay capturas de VPC, EC2 o tablas de rutas reales | Pendiente externo |
| Demostrar ping entre dos instancias | El procedimiento y el script están listos, pero no hay resultado real de dos EC2 | Pendiente externo |

Los pasos operativos, controles de seguridad, capturas requeridas, prueba positiva, prueba negativa y destrucción se encuentran en `handoff.md`. Ningún pendiente debe marcarse como verificado sin evidencia auténtica de la cuenta AWS autorizada.

## Dictamen

La Fase 1 está completa como propuesta técnica, planificación, cálculo, documentación y prototipo validado localmente. Su validación experimental en nube continúa pendiente de credenciales, presupuesto y autorización externos. El PDF no presenta como realizada una implementación que todavía no ocurrió.
