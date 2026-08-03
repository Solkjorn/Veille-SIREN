param([string]$DossierInstallation = "$env:LOCALAPPDATA\Veille-SIREN")
$ErrorActionPreference = "Stop"
$racine = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $DossierInstallation "venv"
New-Item -ItemType Directory -Force -Path $DossierInstallation | Out-Null
$pythonSysteme = Get-Command py -ErrorAction SilentlyContinue
$argumentsPython = @("-3")
if (-not $pythonSysteme) {
  $pythonSysteme = Get-Command python -ErrorAction SilentlyContinue
  $argumentsPython = @()
}
if (-not $pythonSysteme) {
  $pythonSysteme = Get-Command python3 -ErrorAction SilentlyContinue
  $argumentsPython = @()
}
if (-not $pythonSysteme) { throw "Python 3 est requis et doit être accessible dans le PATH." }
& $pythonSysteme.Source @argumentsPython -m venv $venv
$python = Join-Path $venv "Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $racine "requirements.txt")
Push-Location $racine
try {
  & $python -c "from modules.base_donnees import initialiser_base; initialiser_base()"
} finally {
  Pop-Location
}
Write-Host "Veille-SIREN 1.0 installé. Lancez scripts\lancer_interface.ps1."
