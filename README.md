# Proyecto Final de Redes · Fase 1 y preparación de Fase 2

> ### Diseño, subneteo e implementación base de una red empresarial segmentada en AWS.

> ### **Universidad del Valle de Guatemala · CC3067 Redes · Sección 10 · Grupo 1**

El repositorio contiene el informe técnico en LaTeX, diagramas, infraestructura como código con Terraform y evidencias de validación para la Fase 1.

La rama de Fase 2 incorpora la base de red asignada a Pablo Daniel Barillas Moreno: DMZ,
rutas, NACL, Security Groups de integración, variables, outputs, diagrama y validación local.
Los servicios, clientes de prueba y evidencias cloud se integrarán en los bloques de los demás
responsables antes de ejecutar un despliegue.

## Entregables a revisar por parte del auxiliar o del docente correspondiente

- PDF final: [`output/pdf/Proyecto_Final_Fase_1_Grupo_1.pdf`](output/pdf/Proyecto_Final_Fase_1_Grupo_1.pdf)
- Infraestructura: [`infra/terraform/`](infra/terraform/)
- Evidencias: [`evidence/`](evidence/)

## Avance de Fase 2

- Arquitectura: [`docs/fase-final/arquitectura-fase2.md`](docs/fase-final/arquitectura-fase2.md)
- Terraform: [`infra/terraform/`](infra/terraform/)
- Validación local: `python scripts/validate-pablo-phase2.py`

No se debe ejecutar `terraform apply` desde una copia sin estado. Primero se debe auditar AWS
y decidir entre recuperar el estado original, importar recursos existentes o realizar un
despliegue limpio autorizado.

## Integrantes

- Pablo Daniel Barillas Moreno · 22193
- Andrés Rafael Chivalán · 21534
- Roberto Emiliano Otoniel Camposeco Torres · 23968
