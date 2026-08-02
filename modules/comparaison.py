from dataclasses import dataclass

from modules.modele import Societe


@dataclass(frozen=True)
class Changement:
    champ: str
    libelle: str
    ancienne_valeur: str
    nouvelle_valeur: str
    niveau: str = "informatif"
    categorie: str = "autre"
    regle: str = "information générale"


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


PRIORITE_NIVEAUX = {"critique": 0, "important": 1, "informatif": 2}
CATEGORIES_ALERTES = (
    "cessation_radiation", "procedure_collective", "dirigeant", "siege",
    "capital", "comptes", "activite", "forme_juridique", "identite",
    "publication", "autre",
)


def classer_changement(
    champ: str,
    ancienne_valeur: str = "",
    nouvelle_valeur: str = "",
) -> tuple[str, str, str]:
    """Classe un changement avec une règle explicite et reproductible."""
    texte = str(nouvelle_valeur or "").casefold()
    if champ == "statut" and any(
        mot in texte for mot in ("radiée", "radiee", "cessée", "cessee")
    ):
        return "critique", "cessation_radiation", "statut de cessation ou radiation"
    if any(mot in texte for mot in (
        "liquidation judiciaire", "redressement judiciaire",
        "procédure collective", "procedure collective",
        "plan de sauvegarde", "cessation des paiements",
    )):
        return "critique", "procedure_collective", "procédure collective détectée"
    if champ == "dirigeant":
        return "important", "dirigeant", "changement de dirigeant"
    if champ == "adresse" or "transfert du siège" in texte or "transfert de siège" in texte:
        return "important", "siege", "transfert ou changement de siège"
    if champ == "capital" or "capital" in texte:
        return "important", "capital", "modification du capital"
    if "dépôt des comptes" in texte or "depot des comptes" in texte:
        return "important", "comptes", "dépôt de comptes"
    if "activité" in texte or "activite" in texte or "objet social" in texte:
        return "important", "activite", "modification de l'activité"
    if champ == "forme_juridique":
        return "important", "forme_juridique", "modification de la forme juridique"
    if champ == "raison_sociale":
        return "informatif", "identite", "modification de la raison sociale"
    if champ == "derniere_publication_bodacc":
        return "informatif", "publication", "nouvelle publication BODACC"
    return "informatif", "autre", "information générale"


def completer_champs_absents(
    ancienne: Societe | None,
    nouvelle: Societe,
) -> Societe:
    """Préserve un enrichissement antérieur lorsqu'il n'a pas été recollecté."""
    if ancienne is None:
        return nouvelle
    for champ in CHAMPS_SUIVIS:
        valeur_nouvelle = str(getattr(nouvelle, champ, "") or "").strip()
        valeur_ancienne = str(getattr(ancienne, champ, "") or "").strip()
        if valeur_nouvelle or not valeur_ancienne or champ in nouvelle.provenance:
            continue
        setattr(nouvelle, champ, getattr(ancienne, champ))
        source_precedente = ancienne.provenance.get(champ) or ancienne.source
        nouvelle.provenance[champ] = f"Historique ({source_precedente})"
        nouvelle.dates_provenance[champ] = (
            ancienne.dates_provenance.get(champ)
            or ancienne.date_collecte.isoformat(timespec="seconds")
        )
    return nouvelle


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
            niveau, categorie, regle = classer_changement(
                champ, ancienne_valeur, nouvelle_valeur
            )
            changements.append(
                Changement(
                    champ=champ,
                    libelle=libelle,
                    ancienne_valeur=ancienne_valeur,
                    nouvelle_valeur=nouvelle_valeur,
                    niveau=niveau,
                    categorie=categorie,
                    regle=regle,
                )
            )

    return sorted(
        changements,
        key=lambda changement: PRIORITE_NIVEAUX[changement.niveau],
    )
