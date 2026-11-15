# Integración del informe acumulativo

Las secciones integradas de Pablo, Andrés y Roberto están preparadas en:

1. `sections/15-arquitectura-fase2.tex`
2. `sections/16-firewall-nacl.tex`
3. `sections/17-integracion-terraform.tex`
4. `sections/18-dns-intranet.tex`
5. `sections/19-web-publica-hardening.tex`
6. `sections/20-pruebas-seguridad.tex`

Cuando los demás responsables entreguen sus capítulos, el documento maestro deberá incluir:

```tex
\input{sections/15-arquitectura-fase2}
\input{sections/16-firewall-nacl}
\input{sections/17-integracion-terraform}
\input{sections/18-dns-intranet}
\input{sections/19-web-publica-hardening}
\input{sections/20-pruebas-seguridad}
```

Estas secciones describen la arquitectura, las reglas de red, el DNS, la intranet y la web
pública ya verificados localmente. No deben marcar el
despliegue cloud como completado hasta incorporar el plan, `apply`, outputs, pruebas y
capturas genuinas.
