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

CREATE TABLE IF NOT EXISTS taches_collecte (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    siren TEXT NOT NULL,
    statut TEXT NOT NULL,
    tentative INTEGER NOT NULL,
    message TEXT NOT NULL,
    date_evenement TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS index_taches_collecte_siren_date
ON taches_collecte (siren, date_evenement);

CREATE TABLE IF NOT EXISTS configuration_notion (
    cle TEXT PRIMARY KEY,
    valeur TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS publications_notion (
    identifiant TEXT PRIMARY KEY,
    page_id TEXT NOT NULL,
    url TEXT NOT NULL,
    date_publication TEXT NOT NULL
);
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


def lire_collectes_recentes(
    limite: int = 100,
    chemin: Path = BASE_SQLITE,
) -> list[Societe]:
    """Retourne les dernières collectes, toutes sociétés confondues."""
    if limite < 1:
        raise ValueError("La limite doit être positive")
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
            ORDER BY id DESC
            LIMIT ?
            """,
            (limite,),
        ).fetchall()
    return [_convertir_collecte(ligne) for ligne in lignes]


def lire_collectes_entre(
    debut: datetime,
    fin: datetime,
    chemin: Path = BASE_SQLITE,
) -> list[Societe]:
    """Retourne les collectes d'un intervalle, borne de fin exclue."""
    if fin <= debut:
        raise ValueError("La fin de l'intervalle doit suivre son début.")
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
            WHERE date_collecte >= ? AND date_collecte < ?
            ORDER BY date_collecte, id
            """,
            (
                debut.isoformat(timespec="seconds"),
                fin.isoformat(timespec="seconds"),
            ),
        ).fetchall()
    return [_convertir_collecte(ligne) for ligne in lignes]


def lire_collecte_avant(
    siren: str,
    date_limite: datetime,
    chemin: Path = BASE_SQLITE,
) -> Societe | None:
    """Retourne le dernier instantané strictement antérieur à une date."""
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        connexion.row_factory = sqlite3.Row
        ligne = connexion.execute(
            """
            SELECT
                siren, raison_sociale, forme_juridique, capital, statut,
                adresse, dirigeant, derniere_publication_bodacc,
                dernier_changement, source, date_collecte
            FROM collectes
            WHERE siren = ? AND date_collecte < ?
            ORDER BY date_collecte DESC, id DESC
            LIMIT 1
            """,
            (
                str(siren).strip(),
                date_limite.isoformat(timespec="seconds"),
            ),
        ).fetchone()
    return _convertir_collecte(ligne) if ligne is not None else None


def enregistrer_etat_tache(
    siren: str,
    statut: str,
    tentative: int = 1,
    message: str = "",
    chemin: Path = BASE_SQLITE,
) -> None:
    """Conserve un événement du cycle de vie d'une tâche de collecte."""
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        with connexion:
            connexion.execute(
                """
                INSERT INTO taches_collecte (
                    siren, statut, tentative, message, date_evenement
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(siren).strip(),
                    statut,
                    tentative,
                    message,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )


def lire_erreurs_taches_entre(
    debut: datetime,
    fin: datetime,
    chemin: Path = BASE_SQLITE,
) -> list[tuple[str, str]]:
    """Retourne les échecs de collecte enregistrés sur un intervalle."""
    if fin <= debut:
        raise ValueError("La fin de l'intervalle doit suivre son début.")
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        lignes = connexion.execute(
            """
            SELECT siren, message
            FROM taches_collecte
            WHERE statut = 'echec'
              AND date_evenement >= ?
              AND date_evenement < ?
            ORDER BY date_evenement, id
            """,
            (
                debut.isoformat(timespec="seconds"),
                fin.isoformat(timespec="seconds"),
            ),
        ).fetchall()
    return [(ligne[0], ligne[1]) for ligne in lignes]


def configurer_cible_notion(
    cle: str,
    valeur: str,
    chemin: Path = BASE_SQLITE,
) -> None:
    """Conserve un identifiant Notion non sensible dans SQLite."""
    cle, valeur = str(cle).strip(), str(valeur).strip()
    if not cle or not valeur:
        raise ValueError("La clé et la valeur Notion sont requises.")
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        with connexion:
            connexion.execute(
                """
                INSERT INTO configuration_notion (cle, valeur)
                VALUES (?, ?)
                ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur
                """,
                (cle, valeur),
            )


def lire_cible_notion(
    cle: str,
    chemin: Path = BASE_SQLITE,
) -> str:
    """Lit un identifiant de cible Notion depuis SQLite."""
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        ligne = connexion.execute(
            "SELECT valeur FROM configuration_notion WHERE cle = ?",
            (str(cle).strip(),),
        ).fetchone()
    return ligne[0] if ligne else ""


def enregistrer_publication_notion(
    identifiant: str,
    page_id: str,
    url: str,
    chemin: Path = BASE_SQLITE,
) -> None:
    """Mémorise une publication Notion pour empêcher sa duplication."""
    valeurs = tuple(str(v).strip() for v in (identifiant, page_id, url))
    if not all(valeurs):
        raise ValueError("Les informations de publication Notion sont requises.")
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        with connexion:
            connexion.execute(
                """
                INSERT INTO publications_notion (
                    identifiant, page_id, url, date_publication
                ) VALUES (?, ?, ?, ?)
                """,
                (*valeurs, datetime.now().isoformat(timespec="seconds")),
            )


def publication_notion_existe(
    identifiant: str,
    chemin: Path = BASE_SQLITE,
) -> bool:
    """Indique si un rapport a déjà été publié dans Notion."""
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        ligne = connexion.execute(
            "SELECT 1 FROM publications_notion WHERE identifiant = ?",
            (str(identifiant).strip(),),
        ).fetchone()
    return ligne is not None
