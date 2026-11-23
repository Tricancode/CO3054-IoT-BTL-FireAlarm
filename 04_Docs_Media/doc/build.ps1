# Build the report and update the contents, figure list and table list.
$ErrorActionPreference = 'Stop'
$latexCommand = Get-Command pdflatex -ErrorAction SilentlyContinue
if ($latexCommand) {
    $latexExe = $latexCommand.Source
} else {
    $latexExe = Join-Path $env:LOCALAPPDATA 'Programs\MiKTeX\miktex\bin\x64\pdflatex.exe'
}
if (-not (Test-Path -LiteralPath $latexExe)) {
    throw 'pdfLaTeX was not found. Install MiKTeX or TeX Live and add pdflatex to PATH.'
}
Push-Location -LiteralPath $PSScriptRoot
try {
    for ($pass = 1; $pass -le 3; $pass++) {
        & $latexExe -interaction=nonstopmode -halt-on-error -synctex=1 report.tex
        if ($LASTEXITCODE -ne 0) {
            throw "pdfLaTeX failed on pass $pass. See report.log."
        }
    }
} finally {
    Pop-Location
}
