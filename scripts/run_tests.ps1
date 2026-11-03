Write-Host "Running IndusPilot Backend Integration Test Suite..." -ForegroundColor Cyan

$env:PYTHONPATH = "backend"
& "$PSScriptRoot\..\backend\.venv\Scripts\pytest.exe" "$PSScriptRoot\..\backend\tests\test_induspilot_core.py" -v

