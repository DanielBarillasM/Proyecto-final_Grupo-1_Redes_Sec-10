# Proyecto Final de Redes · Fase 1 y Fase 2 en integración

> ### Diseño, subneteo e implementación base de una red empresarial segmentada en AWS.

> ### **Universidad del Valle de Guatemala · CC3067 Redes · Sección 10 · Grupo 1**

El repositorio contiene el informe técnico en LaTeX, diagramas, infraestructura como código con Terraform y evidencias de validación para la Fase 1.

La rama `Roberto-Fasedos` integra la base de red asignada a Pablo Daniel Barillas Moreno (DMZ,
rutas, NACL, Security Groups, variables y outputs), el DNS interno y la intranet de Recursos
Humanos de Andrés Rafael Chivalán, y la web pública de Roberto en la DMZ. Los clientes y pruebas
de Genser y las evidencias cloud se incorporarán antes del despliegue final.

## Entregables a revisar por parte del auxiliar o del docente correspondiente

- PDF final: [`output/pdf/Proyecto_Final_Fase_1_Grupo_1.pdf`](output/pdf/Proyecto_Final_Fase_1_Grupo_1.pdf)
- Infraestructura: [`infra/terraform/`](infra/terraform/)
- Evidencias: [`evidence/`](evidence/)

## Avance de Fase 2

- Arquitectura: [`docs/fase-final/arquitectura-fase2.md`](docs/fase-final/arquitectura-fase2.md)
- Terraform: [`infra/terraform/`](infra/terraform/)
- Validación de red: `python scripts/validate-pablo-phase2.py`
- Validación de DNS e intranet: `python scripts/validate-andres-phase2.py`
- Validación de web pública y hardening: `python scripts/validate-roberto-phase2.py`

No se debe ejecutar `terraform apply` desde una copia sin estado. Primero se debe auditar AWS
y decidir entre recuperar el estado original, importar recursos existentes o realizar un
despliegue limpio autorizado.

## Integrantes

- Pablo Daniel Barillas Moreno · 22193
- Andrés Rafael Chivalán · 21534
- Roberto Emiliano Otoniel Camposeco Torres · 23968
- Genser Catalán · nombre completo y carné pendientes de confirmación
