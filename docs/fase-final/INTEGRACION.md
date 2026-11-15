# Integración del informe acumulativo

Las secciones de Pablo, Andrés, Roberto y Genser están integradas en `main.tex`:

1. `sections/15-arquitectura-fase2.tex`
2. `sections/16-firewall-nacl.tex`
3. `sections/17-integracion-terraform.tex`
4. `sections/18-dns-intranet.tex`
5. `sections/19-web-publica-hardening.tex`
6. `sections/20-pruebas-seguridad.tex`

El documento maestro incluye:

```tex
\input{sections/15-arquitectura-fase2}
\input{sections/16-firewall-nacl}
\input{sections/17-integracion-terraform}
\input{sections/18-dns-intranet}
\input{sections/19-web-publica-hardening}
\input{sections/20-pruebas-seguridad}
\input{sections/21-conclusiones-fase-final}
```

Estas secciones describen la arquitectura, las reglas de red, el DNS, la intranet y la web
pública ya verificados localmente. No deben marcar el
despliegue cloud como completado hasta incorporar el plan, `apply`, outputs, pruebas y
capturas genuinas. Pablo Daniel Barillas Moreno y Andrés Rafael Chivalán son los responsables de
ejecutar F2-01 a F2-13 y recopilar la evidencia; Genser mantiene la automatización si aparece un
defecto reproducible.
