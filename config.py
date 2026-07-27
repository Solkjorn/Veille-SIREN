from pathlib import Path

# Racine du projet
RACINE = Path(__file__).parent

# Dossiers
DOSSIER_DONNEES = RACINE / "donnees"
DOSSIER_RAPPORTS = RACINE / "rapports"
DOSSIER_LOGS = RACINE / "logs"

# Fichiers
FICHIER_SIRENS = DOSSIER_DONNEES / "sirens.xlsx"
BASE_SQLITE = DOSSIER_DONNEES / "veille.sqlite"