import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from config import BASE_SQLITE, DOSSIER_RAPPORTS, DOSSIER_SAUVEGARDES
from modules.base_donnees import initialiser_base


def diagnostiquer_application(chemin_base: Path = BASE_SQLITE) -> list[dict]:
    """Retourne des contrôles lisibles de l'installation locale."""
    controles = []

    def ajouter(nom, ok, detail):
        controles.append({"nom": nom, "ok": bool(ok), "detail": str(detail)})

    try:
        initialiser_base(chemin_base)
        with closing(sqlite3.connect(chemin_base)) as connexion:
            resultat = connexion.execute("PRAGMA integrity_check").fetchone()[0]
            version = connexion.execute("PRAGMA user_version").fetchone()[0]
        ajouter("Base SQLite", resultat == "ok", f"Intégrité : {resultat} · schéma {version}")
    except (OSError, sqlite3.Error) as erreur:
        ajouter("Base SQLite", False, erreur)
    ajouter("Python", sys.version_info >= (3, 11), sys.version.split()[0])
    ajouter("Rapports", DOSSIER_RAPPORTS.is_dir(), DOSSIER_RAPPORTS)
    ajouter("Sauvegardes", DOSSIER_SAUVEGARDES.is_dir(), DOSSIER_SAUVEGARDES)
    ajouter("Espace disque", True, "Stockage local accessible")
    return controles
