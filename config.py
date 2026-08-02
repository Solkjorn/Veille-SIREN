import os
from pathlib import Path

# Racine du projet
RACINE = Path(__file__).parent

# Dossiers
DOSSIER_DONNEES = RACINE / "donnees"
DOSSIER_RAPPORTS = RACINE / "rapports"
DOSSIER_LOGS = RACINE / "logs"
DOSSIER_SAUVEGARDES = Path(
    os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")
) / "Veille-SIREN" / "sauvegardes"

# Fichiers
FICHIER_SIRENS = DOSSIER_DONNEES / "sirens.xlsx"
BASE_SQLITE = DOSSIER_DONNEES / "veille.sqlite"
