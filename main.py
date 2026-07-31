from modules.base_donnees import (
    enregistrer_societe,
    initialiser_base,
    lire_derniere_collecte,
)
from modules.collecteur import CollecteurSocietes
from modules.comparaison import Changement, detecter_changements
from modules.initialisation import creer_dossiers
from modules.logger import logger
from modules.modele import Societe
from modules.rapport import generer_rapport
from modules.societes_surveillees import lire_societes_surveillees
from modules.sources import SOURCES_DISPONIBLES, creer_source


def est_active(valeur) -> bool:
    """
    Indique si une ligne du fichier Excel doit être collectée.
    """
    return str(valeur).strip().lower() in {"1", "oui", "o", "true", "vrai"}


def afficher_societe(societe: Societe) -> None:
    """
    Affiche les informations collectées pour une société.
    """
    print()
    print("===== RÉSULTAT =====")
    print(f"SIREN           : {societe.siren}")
    print(f"Nom             : {societe.raison_sociale}")
    print(f"Forme juridique : {societe.forme_juridique}")
    print(f"Capital         : {societe.capital}")
    print(f"Statut          : {societe.statut}")
    print(f"Adresse         : {societe.adresse}")
    print(f"Dirigeant(s)    : {societe.dirigeant}")
    print(f"Dernier BODACC  : {societe.derniere_publication_bodacc}")
    print(f"Changement      : {societe.dernier_changement}")
    print(f"Source          : {societe.source}")


def afficher_changements(changements: list[Changement]) -> None:
    """
    Affiche les différences entre la collecte précédente et la nouvelle.
    """
    if not changements:
        print("Aucun changement détecté depuis la dernière collecte.")
        return

    print()
    print("===== CHANGEMENTS DÉTECTÉS =====")

    for changement in changements:
        ancienne = changement.ancienne_valeur or "(vide)"
        nouvelle = changement.nouvelle_valeur or "(vide)"
        print(f"{changement.libelle} : {ancienne} -> {nouvelle}")


def executer(sans_interface: bool = False, source: str = "pappers") -> None:
    """
    Lance la veille pour toutes les sociétés actives et valides du fichier.
    """
    logger.info("Démarrage de la veille juridique")

    print("=" * 40)
    print(" VEILLE JURIDIQUE DES SOCIÉTÉS")
    print("=" * 40)
    print()

    creer_dossiers()
    initialiser_base()

    print()
    print("Lecture des sociétés surveillées dans SQLite...")

    societes = lire_societes_surveillees(actives_uniquement=True)
    logger.info("%s société(s) active(s) trouvée(s) dans SQLite", len(societes))
    print(f"{len(societes)} société(s) active(s) trouvée(s).")
    print()

    societes_a_collecter = [societe.siren for societe in societes]
    for societe in societes:
        print(f"[OK] {societe.siren} | Commentaire : {societe.commentaire}")

    if not societes_a_collecter:
        logger.info("Aucune société active avec un SIREN valide")
        print()
        print("Aucune société active avec un SIREN valide à collecter.")
        return

    resultats = []

    with CollecteurSocietes(
        sans_interface=sans_interface,
        tentatives=2,
        source=creer_source(source),
    ) as collecteur:
        for siren in societes_a_collecter:
            logger.info("Début de la collecte du SIREN %s", siren)
            print()
            print(f"Lecture de la société portant le SIREN {siren}...")

            try:
                societe_collectee = collecteur.collecter(siren)

            except Exception as erreur:
                logger.exception("Échec de la collecte du SIREN %s", siren)
                print(f"Échec de la collecte du SIREN {siren} : {erreur}")
                continue

            logger.info("Collecte du SIREN %s terminée avec succès", siren)
            ancienne_collecte = lire_derniere_collecte(siren)
            changements = detecter_changements(
                ancienne_collecte,
                societe_collectee,
            )
            enregistrer_societe(societe_collectee)
            logger.info("Collecte du SIREN %s enregistrée dans SQLite", siren)
            afficher_societe(societe_collectee)
            afficher_changements(changements)
            resultats.append((societe_collectee, changements))

            for changement in changements:
                logger.warning(
                    "Changement pour %s - %s : %r -> %r",
                    siren,
                    changement.libelle,
                    changement.ancienne_valeur,
                    changement.nouvelle_valeur,
                )

    if resultats:
        chemin_rapport = generer_rapport(resultats)
        logger.info("Rapport généré : %s", chemin_rapport)
        print()
        print(f"Rapport enregistré dans : {chemin_rapport}")

    logger.info("Fin de la veille juridique")


if __name__ == "__main__":
    import argparse

    analyseur = argparse.ArgumentParser()
    analyseur.add_argument(
        "--sans-interface",
        action="store_true",
        help="Exécute Chromium sans fenêtre visible.",
    )
    analyseur.add_argument(
        "--source",
        choices=SOURCES_DISPONIBLES,
        default="pappers",
        help="Source juridique utilisée pour la collecte.",
    )
    arguments = analyseur.parse_args()
    executer(
        sans_interface=arguments.sans_interface,
        source=arguments.source,
    )
