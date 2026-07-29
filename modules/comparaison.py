from dataclasses import dataclass

from modules.modele import Societe


@dataclass(frozen=True)
class Changement:
    champ: str
    libelle: str
    ancienne_valeur: str
    nouvelle_valeur: str


CHAMPS_SUIVIS = {
    "raison_sociale": "Raison sociale",
    "forme_juridique": "Forme juridique",
    "capital": "Capital",
    "statut": "Statut",
    "adresse": "Adresse",
    "dirigeant": "Dirigeant(s)",
    "derniere_publication_bodacc": "Dernière publication BODACC",
    "dernier_changement": "Dernier changement",
}


def detecter_changements(
    ancienne: Societe | None,
    nouvelle: Societe,
) -> list[Changement]:
    """
    Compare deux instantanés et retourne les champs ayant changé.

    Une première collecte, sans état antérieur, devient la référence et ne
    produit donc aucune alerte.
    """
    if ancienne is None:
        return []

    changements = []

    for champ, libelle in CHAMPS_SUIVIS.items():
        ancienne_valeur = getattr(ancienne, champ)
        nouvelle_valeur = getattr(nouvelle, champ)

        if ancienne_valeur != nouvelle_valeur:
            changements.append(
                Changement(
                    champ=champ,
                    libelle=libelle,
                    ancienne_valeur=ancienne_valeur,
                    nouvelle_valeur=nouvelle_valeur,
                )
            )

    return changements
