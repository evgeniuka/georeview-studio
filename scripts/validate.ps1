$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$Python = if ($env:GEOREVIEW_PYTHON) { $env:GEOREVIEW_PYTHON } else { "python" }
$Validator = Join-Path $ProjectDir "tests\validate_app.py"

& $Python -B $Validator
