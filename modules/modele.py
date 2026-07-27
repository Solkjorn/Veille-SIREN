from dataclasses import dataclass


@dataclass
class Societe:
    siren: str
    raison_sociale: str = ""
    forme_juridique: str = ""
    capital: str = ""
    adresse: str = ""
    dirigeant: str = ""
    statut: str = ""