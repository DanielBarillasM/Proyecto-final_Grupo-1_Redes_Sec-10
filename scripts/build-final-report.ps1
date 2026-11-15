$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$doc = Join-Path $repo 'docs\fase-final'
$build = Join-Path $doc 'build'
$output = Join-Path $repo 'output\pdf'

New-Item -ItemType Directory -Force -Path $build, $output | Out-Null

python (Join-Path $PSScriptRoot 'generate-figures.py')
if ($LASTEXITCODE -ne 0) { throw 'Falló la generación de diagramas de Fase 1.' }
python (Join-Path $PSScriptRoot 'generate-phase2-figures.py')
if ($LASTEXITCODE -ne 0) { throw 'Falló la generación de diagramas de Fase 2.' }

foreach ($validator in 'validate-network.py', 'validate-pablo-phase2.py',
                       'validate-andres-phase2.py', 'validate-roberto-phase2.py',
                       'validate-phase2.py') {
    python (Join-Path $PSScriptRoot $validator)
    if ($LASTEXITCODE -ne 0) { throw "Falló $validator." }
}

Push-Location $doc
try {
    latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build main.tex
    if ($LASTEXITCODE -ne 0) {
        throw "La compilación LaTeX acumulativa falló con código $LASTEXITCODE."
    }
    Copy-Item -LiteralPath (Join-Path $build 'main.pdf') `
        -Destination (Join-Path $output 'Proyecto_Final_Fases_1_y_2_Grupo_1.pdf') -Force
}
finally {
    Pop-Location
}

Write-Output "PDF generado: $output\Proyecto_Final_Fases_1_y_2_Grupo_1.pdf"
