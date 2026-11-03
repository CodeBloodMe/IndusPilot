Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Starting IndusPilot (Tech4Bharat 2026 - Problem 4.1)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Start FastAPI backend in a separate job
$backendJob = Start-Job -ScriptBlock {
    Set-Location $args[0]
    $env:PYTHONPATH = "backend"
    & "backend\.venv\Scripts\uvicorn.exe" app.main:app --host 0.0.0.0 --port 8000
} -ArgumentList $PSScriptRoot\..

Write-Host "[1/2] Backend starting at http://localhost:8000 (Docs: http://localhost:8000/docs)" -ForegroundColor Green

# 2. Start Next.js frontend
Write-Host "[2/2] Starting Next.js frontend at http://localhost:3000..." -ForegroundColor Green
Set-Location "$PSScriptRoot\..\frontend"
npm run dev

