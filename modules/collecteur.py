from modules.modele import Societe
from modules.pappers import lire_pappers


def collecter_societe(siren: str) -> Societe:
    """
    Collecte les informations disponibles pour une société.

    Pour le moment, la collecte utilise uniquement Pappers.
    D'autres sources seront ajoutées ensuite.
    """

    societe = lire_pappers(siren)

    return societe