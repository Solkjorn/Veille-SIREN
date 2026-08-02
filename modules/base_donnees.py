import hashlib
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from config import BASE_SQLITE
from modules.comparaison import CATEGORIES_ALERTES
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
    provenance TEXT NOT NULL DEFAULT '{}',
    dates_provenance TEXT NOT NULL DEFAULT '{}',
    erreurs_sources TEXT NOT NULL DEFAULT '{}',
    contradictions TEXT NOT NULL DEFAULT '{}',
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

CREATE TABLE IF NOT EXISTS executions_veille (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_execution TEXT NOT NULL,
    source TEXT NOT NULL,
    statut TEXT NOT NULL,
    date_debut TEXT NOT NULL,
    date_fin TEXT,
    societes INTEGER NOT NULL DEFAULT 0,
    modifications INTEGER NOT NULL DEFAULT 0,
    erreurs INTEGER NOT NULL DEFAULT 0,
    rapport TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS alertes (
    identifiant TEXT PRIMARY KEY,
    siren TEXT NOT NULL,
    champ TEXT NOT NULL,
    niveau TEXT NOT NULL,
    categorie TEXT NOT NULL,
    regle TEXT NOT NULL,
    ancienne_valeur TEXT NOT NULL,
    nouvelle_valeur TEXT NOT NULL,
    source TEXT NOT NULL,
    date_detection TEXT NOT NULL,
    statut TEXT NOT NULL DEFAULT 'nouvelle'
);

CREATE INDEX IF NOT EXISTS index_alertes_date_niveau
ON alertes (date_detection DESC, niveau, statut);

CREATE TABLE IF NOT EXISTS preferences_alertes (
    siren TEXT NOT NULL,
    categorie TEXT NOT NULL,
    active INTEGER NOT NULL,
    PRIMARY KEY (siren, categorie)
);

CREATE TABLE IF NOT EXISTS configuration (
    cle TEXT PRIMARY KEY,
    valeur TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents_inpi (
    identifiant TEXT NOT NULL,
    type_document TEXT NOT NULL,
    siren TEXT NOT NULL,
    date_depot TEXT NOT NULL DEFAULT '',
    date_mise_a_jour TEXT NOT NULL DEFAULT '',
    libelle TEXT NOT NULL DEFAULT '',
    nom_document TEXT NOT NULL DEFAULT '',
    confidentialite TEXT NOT NULL DEFAULT '',
    date_detection TEXT NOT NULL,
    PRIMARY KEY (identifiant, type_document)
);

CREATE INDEX IF NOT EXISTS index_documents_inpi_siren_date
ON documents_inpi (siren, date_depot DESC);

CREATE TABLE IF NOT EXISTS portefeuilles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    categorie TEXT NOT NULL DEFAULT '',
    responsable TEXT NOT NULL DEFAULT '',
    regle_surveillance TEXT NOT NULL DEFAULT 'standard',
    destinataire TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS societes_portefeuilles (
    portefeuille_id INTEGER NOT NULL,
    siren TEXT NOT NULL,
    etiquettes TEXT NOT NULL DEFAULT '',
    contact_interne TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (portefeuille_id, siren),
    FOREIGN KEY (portefeuille_id) REFERENCES portefeuilles(id)
);

CREATE TABLE IF NOT EXISTS controle_application (
    cle TEXT PRIMARY KEY,
    valeur TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS journal_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    cible TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT '',
    resultat TEXT NOT NULL DEFAULT 'succes',
    date_action TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS envois_portefeuilles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portefeuille_id INTEGER NOT NULL,
    destinataire TEXT NOT NULL,
    statut TEXT NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    date_envoi TEXT NOT NULL,
    FOREIGN KEY (portefeuille_id) REFERENCES portefeuilles(id)
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
            colonnes = {
                ligne[1] for ligne in connexion.execute("PRAGMA table_info(collectes)")
            }
            for nom in (
                "provenance", "dates_provenance", "erreurs_sources",
                "contradictions",
            ):
                if nom not in colonnes:
                    connexion.execute(
                        f"ALTER TABLE collectes ADD COLUMN {nom} "
                        "TEXT NOT NULL DEFAULT '{}'"
                    )
            colonnes_portefeuilles = {
                ligne[1] for ligne in connexion.execute(
                    "PRAGMA table_info(portefeuilles)"
                )
            }
            if "destinataire" not in colonnes_portefeuilles:
                connexion.execute(
                    "ALTER TABLE portefeuilles ADD COLUMN destinataire "
                    "TEXT NOT NULL DEFAULT ''"
                )
            connexion.execute("PRAGMA user_version = 25")


def enregistrer_alertes(
    siren: str,
    changements: list,
    *,
    source: str = "",
    date_detection: datetime | None = None,
    chemin: Path = BASE_SQLITE,
) -> int:
    """Enregistre les alertes nouvelles et ignore les doublons du même jour."""
    if not changements:
        return 0
    initialiser_base(chemin)
    categories_autorisees = lire_preferences_alertes(siren, chemin)
    date_detection = date_detection or datetime.now()
    ajoutees = 0
    with closing(sqlite3.connect(chemin)) as connexion:
        with connexion:
            for changement in changements:
                if changement.categorie not in categories_autorisees:
                    continue
                empreinte = "|".join((
                    str(siren).strip(), changement.champ,
                    str(changement.ancienne_valeur), str(changement.nouvelle_valeur),
                    date_detection.date().isoformat(),
                ))
                identifiant = hashlib.sha256(empreinte.encode("utf-8")).hexdigest()
                curseur = connexion.execute(
                    """
                    INSERT OR IGNORE INTO alertes (
                        identifiant, siren, champ, niveau, categorie, regle,
                        ancienne_valeur, nouvelle_valeur, source,
                        date_detection, statut
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'nouvelle')
                    """,
                    (
                        identifiant, str(siren).strip(), changement.champ,
                        changement.niveau, changement.categorie, changement.regle,
                        str(changement.ancienne_valeur),
                        str(changement.nouvelle_valeur), str(source),
                        date_detection.isoformat(timespec="seconds"),
                    ),
                )
                ajoutees += curseur.rowcount
    return ajoutees


def lire_preferences_alertes(
    siren: str,
    chemin: Path = BASE_SQLITE,
) -> set[str]:
    """Retourne les catégories actives ; toutes le sont par défaut."""
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        lignes = connexion.execute(
            "SELECT categorie, active FROM preferences_alertes WHERE siren = ?",
            (str(siren).strip(),),
        ).fetchall()
    if not lignes:
        return set(CATEGORIES_ALERTES)
    return {categorie for categorie, active in lignes if active}


def configurer_preferences_alertes(
    siren: str,
    categories_actives,
    chemin: Path = BASE_SQLITE,
) -> set[str]:
    """Remplace atomiquement les préférences d'alerte d'une société."""
    demandees = {str(categorie) for categorie in categories_actives}
    inconnues = demandees - set(CATEGORIES_ALERTES)
    if inconnues:
        raise ValueError(f"Catégorie d'alerte inconnue : {sorted(inconnues)[0]}")
    siren = str(siren).strip()
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        with connexion:
            connexion.execute(
                "DELETE FROM preferences_alertes WHERE siren = ?", (siren,)
            )
            connexion.executemany(
                "INSERT INTO preferences_alertes (siren, categorie, active) "
                "VALUES (?, ?, ?)",
                [
                    (siren, categorie, int(categorie in demandees))
                    for categorie in CATEGORIES_ALERTES
                ],
            )
    return demandees


def alertes_immediates_actives(chemin: Path = BASE_SQLITE) -> bool:
    """Indique si les courriels critiques immédiats sont activés."""
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        ligne = connexion.execute(
            "SELECT valeur FROM configuration WHERE cle = ?",
            ("alertes_immediates",),
        ).fetchone()
    return bool(ligne and ligne[0] == "1")


def configurer_alertes_immediates(
    active: bool, chemin: Path = BASE_SQLITE
) -> bool:
    """Active ou désactive les courriels critiques immédiats."""
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        with connexion:
            connexion.execute(
                "INSERT OR REPLACE INTO configuration (cle, valeur) VALUES (?, ?)",
                ("alertes_immediates", "1" if active else "0"),
            )
    return bool(active)


def lire_alertes(
    limite: int = 100,
    *,
    niveau: str = "",
    statut: str = "",
    siren: str = "",
    chemin: Path = BASE_SQLITE,
) -> list[dict]:
    """Retourne les alertes récentes, filtrables par niveau et état."""
    if limite < 1:
        raise ValueError("La limite doit être positive.")
    conditions, parametres = [], []
    if niveau:
        conditions.append("niveau = ?")
        parametres.append(niveau)
    if statut:
        conditions.append("statut = ?")
        parametres.append(statut)
    if siren:
        conditions.append("siren = ?")
        parametres.append(str(siren).strip())
    filtre = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        connexion.row_factory = sqlite3.Row
        lignes = connexion.execute(
            f"SELECT * FROM alertes{filtre} "
            "ORDER BY CASE niveau WHEN 'critique' THEN 0 "
            "WHEN 'important' THEN 1 ELSE 2 END, date_detection DESC LIMIT ?",
            (*parametres, limite),
        ).fetchall()
    return [dict(ligne) for ligne in lignes]


def changer_statut_alerte(
    identifiant: str,
    statut: str,
    chemin: Path = BASE_SQLITE,
) -> None:
    """Marque une alerte comme nouvelle, lue ou traitée."""
    if statut not in {"nouvelle", "lue", "traitee"}:
        raise ValueError("État d'alerte invalide.")
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        with connexion:
            curseur = connexion.execute(
                "UPDATE alertes SET statut = ? WHERE identifiant = ?",
                (statut, str(identifiant)),
            )
            if curseur.rowcount != 1:
                raise KeyError("Alerte introuvable.")


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
                    provenance,
                    dates_provenance,
                    erreurs_sources,
                    contradictions,
                    date_collecte
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    json.dumps(societe.provenance, ensure_ascii=False, sort_keys=True),
                    json.dumps(societe.dates_provenance, ensure_ascii=False, sort_keys=True),
                    json.dumps(societe.erreurs_sources, ensure_ascii=False, sort_keys=True),
                    json.dumps(societe.contradictions, ensure_ascii=False, sort_keys=True),
                    societe.date_collecte.isoformat(timespec="seconds"),
                ),
            )
            _inserer_documents_inpi(
                connexion, societe.siren, societe.documents_inpi,
                societe.date_collecte,
            )


def _inserer_documents_inpi(connexion, siren, documents, date_detection):
    connexion.executemany(
        """
        INSERT OR REPLACE INTO documents_inpi (
            identifiant, type_document, siren, date_depot,
            date_mise_a_jour, libelle, nom_document, confidentialite,
            date_detection
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [(
            document["identifiant"], document["type_document"], siren,
            document.get("date_depot", ""), document.get("date_mise_a_jour", ""),
            document.get("libelle", ""), document.get("nom_document", ""),
            document.get("confidentialite", ""),
            date_detection.isoformat(timespec="seconds"),
        ) for document in documents],
    )


def enregistrer_documents_inpi(
    siren: str, documents: list[dict], chemin: Path = BASE_SQLITE,
    date_detection: datetime | None = None,
) -> int:
    """Enregistre un inventaire INPI sans créer de nouvelle collecte société."""
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        avant = connexion.total_changes
        with connexion:
            _inserer_documents_inpi(
                connexion, str(siren).strip(), documents,
                date_detection or datetime.now(),
            )
        return connexion.total_changes - avant


def lire_documents_inpi(
    siren: str, chemin: Path = BASE_SQLITE
) -> list[dict]:
    """Retourne les métadonnées documentaires INPI d'une société."""
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        connexion.row_factory = sqlite3.Row
        lignes = connexion.execute(
            "SELECT * FROM documents_inpi WHERE siren = ? "
            "ORDER BY date_depot DESC, date_mise_a_jour DESC",
            (str(siren).strip(),),
        ).fetchall()
    return [dict(ligne) for ligne in lignes]


def lire_document_inpi(
    identifiant: str, type_document: str, chemin: Path = BASE_SQLITE
) -> dict | None:
    """Retourne un document INPI précis, sans télécharger son contenu."""
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        connexion.row_factory = sqlite3.Row
        ligne = connexion.execute(
            "SELECT * FROM documents_inpi WHERE identifiant = ? AND type_document = ?",
            (identifiant, type_document),
        ).fetchone()
    return dict(ligne) if ligne else None


def creer_portefeuille(
    nom, categorie="", responsable="", regle="standard", destinataire="",
    chemin=BASE_SQLITE,
):
    nom = str(nom).strip()
    if not nom:
        raise ValueError("Le nom du portefeuille est obligatoire.")
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        curseur = connexion.execute(
            "INSERT INTO portefeuilles "
            "(nom,categorie,responsable,regle_surveillance,destinataire) "
            "VALUES (?,?,?,?,?)",
            (nom, categorie, responsable, regle, str(destinataire).strip()),
        )
        return curseur.lastrowid


def lire_portefeuilles(chemin=BASE_SQLITE):
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        connexion.row_factory = sqlite3.Row
        lignes = connexion.execute(
            "SELECT p.*, COUNT(sp.siren) AS societes FROM portefeuilles p "
            "LEFT JOIN societes_portefeuilles sp ON sp.portefeuille_id=p.id "
            "GROUP BY p.id ORDER BY p.nom"
        ).fetchall()
    return [dict(x) for x in lignes]


def affecter_portefeuille(portefeuille_id, siren, etiquettes="", contact="", chemin=BASE_SQLITE):
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        connexion.execute(
            "INSERT OR REPLACE INTO societes_portefeuilles VALUES (?,?,?,?)",
            (int(portefeuille_id), str(siren).strip(), etiquettes, contact),
        )


def lire_societes_portefeuille(portefeuille_id, chemin=BASE_SQLITE):
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        connexion.row_factory = sqlite3.Row
        lignes = connexion.execute(
            "SELECT * FROM societes_portefeuilles WHERE portefeuille_id=? ORDER BY siren",
            (int(portefeuille_id),),
        ).fetchall()
    return [dict(x) for x in lignes]


def configurer_destinataire_portefeuille(
    portefeuille_id: int, destinataire: str, chemin: Path = BASE_SQLITE,
) -> None:
    """Configure l'adresse de synthèse propre à un portefeuille."""
    destinataire = str(destinataire).strip()
    if destinataire and not re.fullmatch(
        r"[^\s@]+@[^\s@]+\.[^\s@]+", destinataire
    ):
        raise ValueError("Adresse de réception invalide.")
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        curseur = connexion.execute(
            "UPDATE portefeuilles SET destinataire=? WHERE id=?",
            (destinataire, int(portefeuille_id)),
        )
        if curseur.rowcount != 1:
            raise KeyError("Portefeuille inconnu.")


def lire_documents_inpi_tous(
    recherche: str = "", type_document: str = "", limite: int = 250,
    chemin: Path = BASE_SQLITE, decalage: int = 0,
) -> list[dict]:
    """Recherche les documents INPI de toutes les sociétés."""
    initialiser_base(chemin)
    clauses, parametres = [], []
    if recherche:
        clauses.append(
            "(d.siren LIKE ? OR d.libelle LIKE ? OR d.nom_document LIKE ? "
            "OR EXISTS(SELECT 1 FROM collectes c WHERE c.siren=d.siren "
            "AND c.raison_sociale LIKE ?))"
        )
        motif = f"%{recherche.strip()}%"
        parametres.extend([motif] * 4)
    if type_document:
        clauses.append("d.type_document = ?")
        parametres.append(type_document)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    requete = """SELECT d.*, COALESCE((SELECT c.raison_sociale FROM collectes c
        WHERE c.siren=d.siren ORDER BY c.date_collecte DESC LIMIT 1), '') AS raison_sociale
        FROM documents_inpi d""" + where + " ORDER BY d.date_depot DESC, d.date_detection DESC LIMIT ? OFFSET ?"
    parametres.extend((int(limite), max(0, int(decalage))))
    with closing(sqlite3.connect(chemin)) as connexion:
        connexion.row_factory = sqlite3.Row
        return [dict(x) for x in connexion.execute(requete, parametres).fetchall()]


def compter_documents_inpi(
    recherche: str = "", type_document: str = "", chemin: Path = BASE_SQLITE,
) -> int:
    """Compte les documents correspondant aux filtres du centre documentaire."""
    initialiser_base(chemin)
    clauses, parametres = [], []
    if recherche:
        clauses.append(
            "(d.siren LIKE ? OR d.libelle LIKE ? OR d.nom_document LIKE ? "
            "OR EXISTS(SELECT 1 FROM collectes c WHERE c.siren=d.siren "
            "AND c.raison_sociale LIKE ?))"
        )
        motif = f"%{recherche.strip()}%"
        parametres.extend([motif] * 4)
    if type_document:
        clauses.append("d.type_document = ?")
        parametres.append(type_document)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with closing(sqlite3.connect(chemin)) as connexion:
        return int(connexion.execute(
            "SELECT COUNT(*) FROM documents_inpi d" + where, parametres
        ).fetchone()[0])


def enregistrer_audit(
    action: str, cible: str = "", detail: str = "", resultat: str = "succes",
    chemin: Path = BASE_SQLITE,
) -> None:
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        connexion.execute(
            "INSERT INTO journal_audit(action,cible,detail,resultat,date_action) VALUES(?,?,?,?,?)",
            (action, cible, detail, resultat, datetime.now().isoformat(timespec="seconds")),
        )
        connexion.execute(
            "DELETE FROM journal_audit WHERE date_action < datetime('now', '-365 days')"
        )


def lire_audit(limite: int = 200, chemin: Path = BASE_SQLITE) -> list[dict]:
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        connexion.row_factory = sqlite3.Row
        lignes = connexion.execute(
            "SELECT * FROM journal_audit ORDER BY id DESC LIMIT ?", (int(limite),)
        ).fetchall()
    return [dict(x) for x in lignes]


def enregistrer_envoi_portefeuille(
    portefeuille_id: int, destinataire: str, statut: str, message: str = "",
    chemin: Path = BASE_SQLITE,
) -> None:
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        connexion.execute(
            "INSERT INTO envois_portefeuilles(portefeuille_id,destinataire,statut,message,date_envoi) VALUES(?,?,?,?,?)",
            (int(portefeuille_id), destinataire, statut, message, datetime.now().isoformat(timespec="seconds")),
        )


def lire_taches_recentes(limite=100, chemin=BASE_SQLITE):
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        connexion.row_factory = sqlite3.Row
        lignes = connexion.execute(
            "SELECT * FROM taches_collecte ORDER BY id DESC LIMIT ?", (int(limite),)
        ).fetchall()
    return [dict(x) for x in lignes]


def demander_arret_collecte(active=True, chemin=BASE_SQLITE):
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion, connexion:
        connexion.execute(
            "INSERT OR REPLACE INTO controle_application VALUES ('arret_collecte', ?)",
            ("1" if active else "0",),
        )


def arret_collecte_demande(chemin=BASE_SQLITE):
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        ligne = connexion.execute(
            "SELECT valeur FROM controle_application WHERE cle='arret_collecte'"
        ).fetchone()
    return bool(ligne and ligne[0] == "1")


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
                provenance,
                dates_provenance,
                erreurs_sources,
                contradictions,
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
    def lire_json(nom: str) -> dict:
        if nom not in ligne.keys():
            return {}
        try:
            return json.loads(ligne[nom] or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}

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
        provenance=lire_json("provenance"),
        dates_provenance=lire_json("dates_provenance"),
        erreurs_sources=lire_json("erreurs_sources"),
        contradictions=lire_json("contradictions"),
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
                dernier_changement, source, provenance, dates_provenance,
                erreurs_sources, contradictions, date_collecte
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
                dernier_changement, source, provenance, dates_provenance,
                erreurs_sources, contradictions, date_collecte
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
                dernier_changement, source, provenance, dates_provenance,
                erreurs_sources, contradictions, date_collecte
            FROM collectes
            WHERE date_collecte >= ? AND date_collecte < ?
            ORDER BY date_collecte, id
            """,
            (
                debut.isoformat(timespec="microseconds"),
                fin.isoformat(timespec="microseconds"),
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
                dernier_changement, source, provenance, dates_provenance,
                erreurs_sources, contradictions, date_collecte
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


def demarrer_execution_veille(
    type_execution: str,
    source: str,
    chemin: Path = BASE_SQLITE,
) -> int:
    """Ouvre une exécution globale et retourne son identifiant."""
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        with connexion:
            curseur = connexion.execute(
                """INSERT INTO executions_veille (
                    type_execution, source, statut, date_debut
                ) VALUES (?, ?, 'en_cours', ?)""",
                (type_execution, source, datetime.now().isoformat(timespec="seconds")),
            )
            return curseur.lastrowid


def terminer_execution_veille(
    identifiant: int,
    statut: str,
    societes: int = 0,
    modifications: int = 0,
    erreurs: int = 0,
    rapport: str = "",
    message: str = "",
    chemin: Path = BASE_SQLITE,
) -> None:
    """Clôture une exécution globale avec son bilan."""
    if statut not in {"succes", "echec"}:
        raise ValueError("Le statut final doit être succes ou echec.")
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        with connexion:
            curseur = connexion.execute(
                """UPDATE executions_veille SET
                    statut = ?, date_fin = ?, societes = ?, modifications = ?,
                    erreurs = ?, rapport = ?, message = ? WHERE id = ?""",
                (
                    statut, datetime.now().isoformat(timespec="seconds"),
                    societes, modifications, erreurs, str(rapport), message,
                    identifiant,
                ),
            )
            if curseur.rowcount != 1:
                raise KeyError(f"Exécution inconnue : {identifiant}")


def lire_executions_veille(
    limite: int = 20,
    chemin: Path = BASE_SQLITE,
) -> list[dict]:
    """Retourne les exécutions globales les plus récentes."""
    initialiser_base(chemin)
    with closing(sqlite3.connect(chemin)) as connexion:
        connexion.row_factory = sqlite3.Row
        lignes = connexion.execute(
            "SELECT * FROM executions_veille ORDER BY id DESC LIMIT ?", (limite,)
        ).fetchall()
    return [dict(ligne) for ligne in lignes]
