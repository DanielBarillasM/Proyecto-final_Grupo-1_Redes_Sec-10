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
pública verificados localmente y en la ventana AWS del 17 de noviembre de 2026. Andrés Rafael
Chivalán ejecutó las pruebas y recopiló la evidencia; Pablo Daniel Barillas Moreno revisó e integró
los resultados. Genser mantiene la automatización si aparece un defecto reproducible. La versión
final registra 36 resultados correctos, 3 omisiones documentadas y el inventario posterior al
cierre.
