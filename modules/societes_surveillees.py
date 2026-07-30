import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from config import BASE_SQLITE
from modules.base_donnees import initialiser_base
from modules.modele import SocieteSurveillee
from modules.validation import siren_valide

SCRIPT_CREATION = """
CREATE TABLE IF NOT EXISTS societes_surveillees (
    siren TEXT PRIMARY KEY,
    actif INTEGER NOT NULL DEFAULT 1 CHECK (actif IN (0, 1)),
    commentaire TEXT NOT NULL DEFAULT '',
    date_creation TEXT NOT NULL,
    date_modification TEXT NOT NULL,
    date_archivage TEXT
);
CREATE INDEX IF NOT EXISTS index_societes_surveillees_actif
ON societes_surveillees (actif, date_archivage);
"""


def initialiser_societes_surveillees(chemin: Path = BASE_SQLITE) -> None:
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        with connexion:
            connexion.executescript(SCRIPT_CREATION)


def _normaliser_siren(siren: str) -> str:
    siren = str(siren).strip()
    if not siren_valide(siren):
        raise ValueError(f"SIREN invalide : {siren}")
    return siren


def _convertir(ligne: sqlite3.Row) -> SocieteSurveillee:
    return SocieteSurveillee(
        siren=ligne["siren"], actif=bool(ligne["actif"]),
        commentaire=ligne["commentaire"],
        date_creation=datetime.fromisoformat(ligne["date_creation"]),
        date_modification=datetime.fromisoformat(ligne["date_modification"]),
        date_archivage=(datetime.fromisoformat(ligne["date_archivage"])
                        if ligne["date_archivage"] else None),
    )


def ajouter_societe_surveillee(siren: str, actif: bool = True,
                                commentaire: str = "",
                                chemin: Path = BASE_SQLITE) -> SocieteSurveillee:
    """Ajoute une société et refuse les SIREN invalides ou en double."""
    siren = _normaliser_siren(siren)
    maintenant = datetime.now().isoformat(timespec="seconds")
    initialiser_societes_surveillees(chemin)
    try:
        with closing(sqlite3.connect(chemin)) as connexion:
            with connexion:
                connexion.execute(
                    """INSERT INTO societes_surveillees
                    (siren, actif, commentaire, date_creation,
                     date_modification, date_archivage)
                    VALUES (?, ?, ?, ?, ?, NULL)""",
                    (siren, int(bool(actif)), str(commentaire or ""),
                     maintenant, maintenant),
                )
    except sqlite3.IntegrityError as erreur:
        raise ValueError(f"Le SIREN {siren} est déjà surveillé") from erreur
    return lire_societe_surveillee(siren, chemin)


def lire_societe_surveillee(siren: str, chemin: Path = BASE_SQLITE
                            ) -> SocieteSurveillee | None:
    initialiser_societes_surveillees(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        connexion.row_factory = sqlite3.Row
        ligne = connexion.execute(
            "SELECT * FROM societes_surveillees WHERE siren = ?",
            (str(siren).strip(),),
        ).fetchone()
    return _convertir(ligne) if ligne else None


def lire_societes_surveillees(actives_uniquement: bool = False,
                              inclure_archivees: bool = False,
                              chemin: Path = BASE_SQLITE
                              ) -> list[SocieteSurveillee]:
    initialiser_societes_surveillees(chemin)
    conditions = []
    if actives_uniquement:
        conditions.append("actif = 1")
    if not inclure_archivees:
        conditions.append("date_archivage IS NULL")
    filtre = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    with closing(sqlite3.connect(chemin)) as connexion:
        connexion.row_factory = sqlite3.Row
        lignes = connexion.execute(
            f"SELECT * FROM societes_surveillees{filtre} ORDER BY siren"
        ).fetchall()
    return [_convertir(ligne) for ligne in lignes]


def modifier_societe_surveillee(siren: str, *, actif: bool | None = None,
                                commentaire: str | None = None,
                                chemin: Path = BASE_SQLITE
                                ) -> SocieteSurveillee:
    siren = _normaliser_siren(siren)
    existante = lire_societe_surveillee(siren, chemin)
    if existante is None or existante.date_archivage is not None:
        raise KeyError(f"Société surveillée introuvable : {siren}")
    nouvel_actif = existante.actif if actif is None else bool(actif)
    nouveau_commentaire = (existante.commentaire if commentaire is None
                            else str(commentaire))
    maintenant = datetime.now().isoformat(timespec="seconds")
    with closing(sqlite3.connect(chemin)) as connexion:
        with connexion:
            connexion.execute(
                """UPDATE societes_surveillees
                SET actif = ?, commentaire = ?, date_modification = ?
                WHERE siren = ? AND date_archivage IS NULL""",
                (int(nouvel_actif), nouveau_commentaire, maintenant, siren),
            )
    return lire_societe_surveillee(siren, chemin)


def activer_societe_surveillee(siren: str, chemin: Path = BASE_SQLITE
                               ) -> SocieteSurveillee:
    """Active une société non archivée."""
    return modifier_societe_surveillee(siren, actif=True, chemin=chemin)


def desactiver_societe_surveillee(siren: str, chemin: Path = BASE_SQLITE
                                  ) -> SocieteSurveillee:
    """Désactive une société non archivée sans l'archiver."""
    return modifier_societe_surveillee(siren, actif=False, chemin=chemin)


def supprimer_societe_surveillee(siren: str, chemin: Path = BASE_SQLITE
                                 ) -> SocieteSurveillee:
    """Archive une société sans détruire son historique."""
    siren = _normaliser_siren(siren)
    existante = lire_societe_surveillee(siren, chemin)
    if existante is None or existante.date_archivage is not None:
        raise KeyError(f"Société surveillée introuvable : {siren}")
    maintenant = datetime.now().isoformat(timespec="seconds")
    with closing(sqlite3.connect(chemin)) as connexion:
        with connexion:
            connexion.execute(
                """UPDATE societes_surveillees
                SET actif = 0, date_modification = ?, date_archivage = ?
                WHERE siren = ? AND date_archivage IS NULL""",
                (maintenant, maintenant, siren),
            )
    return lire_societe_surveillee(siren, chemin)


def restaurer_societe_surveillee(siren: str, *, actif: bool = True,
                                 chemin: Path = BASE_SQLITE
                                 ) -> SocieteSurveillee:
    """Restaure une société archivée et la réactive par défaut."""
    siren = _normaliser_siren(siren)
    existante = lire_societe_surveillee(siren, chemin)
    if existante is None or existante.date_archivage is None:
        raise KeyError(f"Société archivée introuvable : {siren}")
    maintenant = datetime.now().isoformat(timespec="seconds")
    with closing(sqlite3.connect(chemin)) as connexion:
        with connexion:
            connexion.execute(
                """UPDATE societes_surveillees
                SET actif = ?, date_modification = ?, date_archivage = NULL
                WHERE siren = ? AND date_archivage IS NOT NULL""",
                (int(bool(actif)), maintenant, siren),
            )
    return lire_societe_surveillee(siren, chemin)
