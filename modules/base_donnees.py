import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from config import BASE_SQLITE
from modules.modele import Societe


SCRIPT_CREATION = """
CREATE TABLE IF NOT EXISTS collectes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    siren TEXT NOT NULL,
    raison_sociale TEXT NOT NULL,
    forme_juridique TEXT NOT NULL,
    capital TEXT NOT NULL,
    statut TEXT NOT NULL,
    adresse TEXT NOT NULL,
    dirigeant TEXT NOT NULL,
    derniere_publication_bodacc TEXT NOT NULL,
    dernier_changement TEXT NOT NULL,
    source TEXT NOT NULL,
    date_collecte TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS index_collectes_siren_date
ON collectes (siren, date_collecte);
"""


def initialiser_base(chemin: Path = BASE_SQLITE) -> None:
    """
    Crée la base SQLite et sa table de collectes si nécessaire.
    """
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(chemin)) as connexion:
        with connexion:
            connexion.executescript(SCRIPT_CREATION)


def enregistrer_societe(
    societe: Societe,
    chemin: Path = BASE_SQLITE,
) -> None:
    """
    Enregistre un instantané horodaté des données d'une société.
    """
    initialiser_base(chemin)

    with closing(sqlite3.connect(chemin)) as connexion:
        with connexion:
            connexion.execute(
                """
                INSERT INTO collectes (
                    siren,
                    raison_sociale,
                    forme_juridique,
                    capital,
                    statut,
                    adresse,
                    dirigeant,
                    derniere_publication_bodacc,
                    dernier_changement,
                    source,
                    date_collecte
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    societe.siren,
                    societe.raison_sociale,
                    societe.forme_juridique,
                    societe.capital,
                    societe.statut,
                    societe.adresse,
                    societe.dirigeant,
                    societe.derniere_publication_bodacc,
                    societe.dernier_changement,
                    societe.source,
                    societe.date_collecte.isoformat(timespec="seconds"),
                ),
            )


def lire_derniere_collecte(
    siren: str,
    chemin: Path = BASE_SQLITE,
) -> Societe | None:
    """
    Retourne le dernier instantané enregistré pour un SIREN.
    """
    initialiser_base(chemin)

    with closing(sqlite3.connect(chemin)) as connexion:
        connexion.row_factory = sqlite3.Row
        ligne = connexion.execute(
            """
            SELECT
                siren,
                raison_sociale,
                forme_juridique,
                capital,
                statut,
                adresse,
                dirigeant,
                derniere_publication_bodacc,
                dernier_changement,
                source,
                date_collecte
            FROM collectes
            WHERE siren = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (siren,),
        ).fetchone()

    if ligne is None:
        return None

    return _convertir_collecte(ligne)


def _convertir_collecte(ligne: sqlite3.Row) -> Societe:
    return Societe(
        siren=ligne["siren"],
        raison_sociale=ligne["raison_sociale"],
        forme_juridique=ligne["forme_juridique"],
        capital=ligne["capital"],
        statut=ligne["statut"],
        adresse=ligne["adresse"],
        dirigeant=ligne["dirigeant"],
        derniere_publication_bodacc=ligne[
            "derniere_publication_bodacc"
        ],
        dernier_changement=ligne["dernier_changement"],
        source=ligne["source"],
        date_collecte=datetime.fromisoformat(ligne["date_collecte"]),
    )


def lire_collectes_societe(
    siren: str,
    chemin: Path = BASE_SQLITE,
) -> list[Societe]:
    """Retourne tout l'historique d'un SIREN, du plus ancien au plus récent."""
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        connexion.row_factory = sqlite3.Row
        lignes = connexion.execute(
            """
            SELECT
                siren, raison_sociale, forme_juridique, capital, statut,
                adresse, dirigeant, derniere_publication_bodacc,
                dernier_changement, source, date_collecte
            FROM collectes
            WHERE siren = ?
            ORDER BY id
            """,
            (str(siren).strip(),),
        ).fetchall()
    return [_convertir_collecte(ligne) for ligne in lignes]
