$ErrorActionPreference = "Stop"
$racine = Split-Path -Parent $PSScriptRoot
$python = Join-Path $env:LOCALAPPDATA "Veille-SIREN\venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Installez d'abord Veille-SIREN." }
Push-Location $racine
try {
  & $python main.py --sauvegarder
  & $python -m pip install -r requirements.txt
  & $python -c "from modules.base_donnees import initialiser_base; initialiser_base()"
  & $python -m unittest discover -s tests -q
} finally { Pop-Location }
Write-Host "Mise à jour terminée et données préservées."
