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
    date_collecte: datetime = field(default_factory=datetime.now)