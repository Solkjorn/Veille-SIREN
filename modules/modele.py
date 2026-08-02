from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Societe:

    # Identification
    siren: str
    raison_sociale: str = ""

    # Informations juridiques
    forme_juridique: str = ""
    capital: str = ""
    statut: str = ""

    # Coordonnées
    adresse: str = ""

    # Direction
    dirigeant: str = ""

    # Veille
    derniere_publication_bodacc: str = ""
    dernier_changement: str = ""

    # Métadonnées
    source: str = ""
    provenance: dict[str, str] = field(default_factory=dict)
    dates_provenance: dict[str, str] = field(default_factory=dict)
    erreurs_sources: dict[str, str] = field(default_factory=dict)
    contradictions: dict[str, dict[str, str]] = field(default_factory=dict)
    documents_inpi: list[dict] = field(default_factory=list)
    date_collecte: datetime = field(default_factory=datetime.now)

@dataclass
class SocieteSurveillee:
    siren: str
    actif: bool = True
    commentaire: str = ""
    date_creation: datetime = field(default_factory=datetime.now)
    date_modification: datetime = field(default_factory=datetime.now)
    date_archivage: datetime | None = None
