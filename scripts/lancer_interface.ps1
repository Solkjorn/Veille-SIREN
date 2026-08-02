$racine = Split-Path -Parent $PSScriptRoot
$python = Join-Path $env:LOCALAPPDATA "Veille-SIREN\venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Environnement Python Veille-SIREN introuvable."
    exit 1
}
Start-Process -FilePath $python -ArgumentList "-m","webapp" -WorkingDirectory $racine -WindowStyle Hidden
Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:5000/"
