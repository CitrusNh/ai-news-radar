$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendCommand = "python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000"
$FrontendCommand = "python -m http.server 4173 --directory frontend"

Write-Host "Starting SignalScope AI backend at http://127.0.0.1:8000"
Start-Process -FilePath "powershell" -ArgumentList "-NoProfile", "-Command", $BackendCommand -WorkingDirectory $ProjectRoot -WindowStyle Hidden

Write-Host "Starting SignalScope AI frontend at http://127.0.0.1:4173"
Start-Process -FilePath "powershell" -ArgumentList "-NoProfile", "-Command", $FrontendCommand -WorkingDirectory $ProjectRoot -WindowStyle Hidden

Write-Host "Demo services started. API docs: http://127.0.0.1:8000/docs"
