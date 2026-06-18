$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$Python = if ($env:GEOREVIEW_PYTHON) { $env:GEOREVIEW_PYTHON } else { "python" }
$App = Join-Path $ProjectDir "backend\app.py"

& $Python $App
