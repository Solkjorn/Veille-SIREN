import json
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime
from pathlib import Path

from config import BASE_SQLITE, DOSSIER_RAPPORTS, DOSSIER_SAUVEGARDES
from modules.secrets_windows import DOSSIER_SECRETS


class ErreurSauvegarde(RuntimeError):
    """Signale qu'une sauvegarde locale n'a pas pu être créée ou vérifiée."""


def _verifier_noms_archive(noms: list[str]) -> None:
    for nom in noms:
        chemin = Path(nom)
        if chemin.is_absolute() or ".." in chemin.parts or "\\" in nom:
            raise ErreurSauvegarde(f"Chemin non sûr dans l'archive : {nom}")


def _copier_sqlite(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise ErreurSauvegarde(f"Base SQLite introuvable : {source}")
    try:
        with closing(sqlite3.connect(source)) as entree:
            with closing(sqlite3.connect(destination)) as sortie:
                entree.backup(sortie)
                sortie.commit()
    except sqlite3.Error as erreur:
        raise ErreurSauvegarde(f"Copie SQLite impossible : {erreur}") from erreur


def _nettoyer_anciennes_sauvegardes(dossier: Path, conserver: int) -> None:
    if conserver < 1:
        raise ValueError("Le nombre de sauvegardes à conserver doit être positif.")
    archives = sorted(
        dossier.glob("veille-siren_*.zip"),
        key=lambda chemin: chemin.stat().st_mtime,
        reverse=True,
    )
    for archive in archives[conserver:]:
        archive.unlink()


def creer_sauvegarde(
    *,
    chemin_base: Path = BASE_SQLITE,
    dossier_rapports: Path = DOSSIER_RAPPORTS,
    dossier_secrets: Path = DOSSIER_SECRETS,
    dossier_destination: Path = DOSSIER_SAUVEGARDES,
    date_sauvegarde: datetime | None = None,
    conserver: int = 12,
) -> Path:
    """Crée et vérifie une archive locale des données utiles de l'application."""
    date_sauvegarde = date_sauvegarde or datetime.now()
    chemin_base = Path(chemin_base)
    dossier_rapports = Path(dossier_rapports)
    dossier_secrets = Path(dossier_secrets)
    dossier_destination = Path(dossier_destination)
    dossier_destination.mkdir(parents=True, exist_ok=True)
    nom = f"veille-siren_{date_sauvegarde.strftime('%Y%m%d_%H%M%S')}.zip"
    destination = dossier_destination / nom

    with tempfile.TemporaryDirectory(dir=dossier_destination) as temporaire:
        copie_base = Path(temporaire) / "veille.sqlite"
        _copier_sqlite(chemin_base, copie_base)
        fichiers = [(copie_base, "donnees/veille.sqlite")]
        if dossier_rapports.is_dir():
            fichiers.extend(
                (fichier, f"rapports/{fichier.name}")
                for fichier in sorted(dossier_rapports.iterdir())
                if fichier.is_file() and fichier.suffix.casefold() in {".html", ".md"}
            )
        if dossier_secrets.is_dir():
            fichiers.extend(
                (fichier, f"secrets/{fichier.name}")
                for fichier in sorted(dossier_secrets.glob("*.bin"))
                if fichier.is_file()
            )
        manifeste = {
            "application": "Veille-SIREN",
            "date": date_sauvegarde.isoformat(timespec="seconds"),
            "fichiers": [nom_archive for _, nom_archive in fichiers],
            "note_secrets": "Les fichiers .bin restent chiffrés par Windows DPAPI.",
        }
        try:
            with zipfile.ZipFile(destination, "x", zipfile.ZIP_DEFLATED) as archive:
                for fichier, nom_archive in fichiers:
                    archive.write(fichier, nom_archive)
                archive.writestr(
                    "manifest.json",
                    json.dumps(manifeste, ensure_ascii=False, indent=2),
                )
            with zipfile.ZipFile(destination) as archive:
                erreur = archive.testzip()
                if erreur:
                    raise ErreurSauvegarde(f"Fichier corrompu dans l'archive : {erreur}")
        except (OSError, zipfile.BadZipFile) as erreur:
            destination.unlink(missing_ok=True)
            raise ErreurSauvegarde(f"Création de l'archive impossible : {erreur}") from erreur

    _nettoyer_anciennes_sauvegardes(dossier_destination, conserver)
    return destination


def verifier_restauration(archive: Path) -> dict:
    """Restaure temporairement une archive et vérifie l'intégrité de SQLite."""
    archive = Path(archive)
    if not archive.is_file():
        raise ErreurSauvegarde(f"Sauvegarde introuvable : {archive}")
    try:
        with zipfile.ZipFile(archive) as contenu:
            noms = contenu.namelist()
            _verifier_noms_archive(noms)
            if contenu.testzip():
                raise ErreurSauvegarde("La sauvegarde contient un fichier corrompu.")
            requis = {"manifest.json", "donnees/veille.sqlite"}
            if not requis.issubset(noms):
                raise ErreurSauvegarde("La sauvegarde est incomplète.")
            manifeste = json.loads(contenu.read("manifest.json"))
            if manifeste.get("application") != "Veille-SIREN":
                raise ErreurSauvegarde("Le manifeste ne correspond pas à Veille-SIREN.")
            with tempfile.TemporaryDirectory() as temporaire:
                cible = Path(temporaire) / "restauration"
                contenu.extractall(cible)
                base = cible / "donnees" / "veille.sqlite"
                with closing(sqlite3.connect(base)) as connexion:
                    integrite = connexion.execute("PRAGMA integrity_check").fetchone()[0]
                    tables = connexion.execute(
                        "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                    ).fetchone()[0]
                if integrite != "ok":
                    raise ErreurSauvegarde(f"Base SQLite invalide : {integrite}")
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError) as erreur:
        raise ErreurSauvegarde(f"Vérification impossible : {erreur}") from erreur
    return {
        "archive": str(archive),
        "date": manifeste.get("date", ""),
        "fichiers": len(noms),
        "tables": tables,
        "integrite": "ok",
    }
