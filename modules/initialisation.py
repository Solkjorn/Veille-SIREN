from pathlib import Path

def creer_dossiers():
    """
    Crée automatiquement les dossiers nécessaires au projet.
    """

    dossiers = [
        "donnees",
        "rapports",
        "logs",
        "historique",
        "modules"
    ]

    for dossier in dossiers:
        Path(dossier).mkdir(exist_ok=True)
        print(f"📁 {dossier}")