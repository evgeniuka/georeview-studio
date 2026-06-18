$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$Python = if ($env:GEOREVIEW_PYTHON) { $env:GEOREVIEW_PYTHON } else { "python" }
$Generator = Join-Path $ProjectDir "scripts\generate_portfolio_artifacts.py"

& $Python -B $Generator
