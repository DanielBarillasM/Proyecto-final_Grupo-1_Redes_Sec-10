# Integración del informe acumulativo

Las secciones del bloque de Pablo están preparadas en:

1. `sections/15-arquitectura-fase2.tex`
2. `sections/16-firewall-nacl.tex`
3. `sections/17-integracion-terraform.tex`

Cuando los demás responsables entreguen sus capítulos, el documento maestro deberá incluir:

```tex
\input{sections/15-arquitectura-fase2}
\input{sections/16-firewall-nacl}
\input{sections/17-integracion-terraform}
```

Estas secciones describen únicamente resultados locales ya verificados. No deben marcar el
despliegue cloud como completado hasta incorporar el plan, `apply`, outputs, pruebas y
capturas genuinas.
