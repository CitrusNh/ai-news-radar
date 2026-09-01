$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendCommand = "python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000"

Write-Host "Starting SignalScope AI website at http://127.0.0.1:8000"
Start-Process -FilePath "powershell" -ArgumentList "-NoProfile", "-Command", $BackendCommand -WorkingDirectory $ProjectRoot -WindowStyle Hidden
Write-Host "Website started. Home: http://127.0.0.1:8000  API docs: http://127.0.0.1:8000/docs"
