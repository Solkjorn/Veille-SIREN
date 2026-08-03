param([switch]$SupprimerDonnees)
$ErrorActionPreference = "Stop"
$installation = Join-Path $env:LOCALAPPDATA "Veille-SIREN"
if (-not (Test-Path -LiteralPath $installation)) { Write-Host "Aucune installation locale."; exit 0 }
if ($SupprimerDonnees) {
  Write-Warning "La suppression des données doit être effectuée manuellement après vérification d'une sauvegarde."
  exit 2
}
$venv = Join-Path $installation "venv"
$installationResolue = [System.IO.Path]::GetFullPath($installation)
$venvResolu = [System.IO.Path]::GetFullPath($venv)
if (-not $venvResolu.StartsWith($installationResolue + [System.IO.Path]::DirectorySeparatorChar)) {
  throw "Chemin de désinstallation incohérent."
}
if (Test-Path -LiteralPath $venvResolu) { Remove-Item -LiteralPath $venvResolu -Recurse -Force }
Write-Host "Programme désinstallé. Les données, secrets et sauvegardes sont conservés."
