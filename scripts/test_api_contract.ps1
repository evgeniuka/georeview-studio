$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$Python = if ($env:GEOREVIEW_PYTHON) { $env:GEOREVIEW_PYTHON } else { "python" }
$ContractTest = Join-Path $ProjectDir "tests\test_api_contract.py"

& $Python -B $ContractTest
