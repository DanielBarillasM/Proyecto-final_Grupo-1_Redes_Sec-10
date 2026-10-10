$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$doc = Join-Path $repo 'docs\fase-1'
$build = Join-Path $doc 'build'
$output = Join-Path $repo 'output\pdf'

New-Item -ItemType Directory -Force -Path $build, $output | Out-Null

python (Join-Path $PSScriptRoot 'generate-figures.py')
if ($LASTEXITCODE -ne 0) { throw 'Falló la generación de diagramas.' }
python (Join-Path $PSScriptRoot 'validate-network.py')
if ($LASTEXITCODE -ne 0) { throw 'Falló la validación de red.' }
python (Join-Path $PSScriptRoot 'generate-evidence-images.py')
if ($LASTEXITCODE -ne 0) { throw 'Falló la generación de capturas de evidencia.' }

Push-Location $doc
try {
    latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build main.tex
    if ($LASTEXITCODE -ne 0) {
        throw "La compilación LaTeX falló con código $LASTEXITCODE."
    }
    Copy-Item -LiteralPath (Join-Path $build 'main.pdf') -Destination (Join-Path $output 'Proyecto_Final_Fase_1_Grupo_1.pdf') -Force
}
finally {
    Pop-Location
}

Write-Output "PDF generado: $output\Proyecto_Final_Fase_1_Grupo_1.pdf"
