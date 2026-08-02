from modules.base_donnees import (
    arret_collecte_demande,
    demander_arret_collecte,
    alertes_immediates_actives,
    enregistrer_alertes,
    demarrer_execution_veille,
    enregistrer_societe,
    initialiser_base,
    lire_derniere_collecte,
    lire_portefeuilles,
    lire_societes_portefeuille,
    enregistrer_envoi_portefeuille,
    terminer_execution_veille,
)
from modules.collecteur import CollecteurSocietes
from modules.comparaison import (
    Changement, completer_champs_absents, detecter_changements,
)
from modules.courriel import ErreurCourriel, envoyer_alerte_critique, envoyer_synthese
from modules.initialisation import creer_dossiers
from modules.logger import logger
from modules.modele import Societe
from modules.notion import (
    ErreurNotion,
    publier_rapport_veille,
    publier_synthese_hebdomadaire,
)
from modules.rapport import (
    generer_rapport, generer_synthese_hebdomadaire,
    generer_synthese_portefeuille, lire_resume_rapport_html,
)
from modules.sauvegarde import ErreurSauvegarde, creer_sauvegarde
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


def executer(sans_interface: bool = False, source: str = "pappers", sirens=None):
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

    filtre_sirens = {str(s).strip() for s in (sirens or [])}
    societes_a_collecter = [societe.siren for societe in societes if not filtre_sirens or societe.siren in filtre_sirens]
    for societe in societes:
        print(f"[OK] {societe.siren} | Commentaire : {societe.commentaire}")

    if not societes_a_collecter:
        logger.info("Aucune société active avec un SIREN valide")
        print()
        print("Aucune société active avec un SIREN valide à collecter.")
        return

    resultats = []
    erreurs_collecte = []

    with CollecteurSocietes(
        sans_interface=sans_interface,
        tentatives=2,
        source=creer_source(source),
    ) as collecteur:
        for siren in societes_a_collecter:
            if arret_collecte_demande():
                logger.warning("Arrêt propre demandé avant le SIREN %s", siren)
                break
            logger.info("Début de la collecte du SIREN %s", siren)
            print()
            print(f"Lecture de la société portant le SIREN {siren}...")

            try:
                societe_collectee = collecteur.collecter(siren)

            except Exception as erreur:
                logger.exception("Échec de la collecte du SIREN %s", siren)
                print(f"Échec de la collecte du SIREN {siren} : {erreur}")
                erreurs_collecte.append((siren, str(erreur)))
                continue

            logger.info("Collecte du SIREN %s terminée avec succès", siren)
            ancienne_collecte = lire_derniere_collecte(siren)
            completer_champs_absents(ancienne_collecte, societe_collectee)
            changements = detecter_changements(
                ancienne_collecte,
                societe_collectee,
            )
            enregistrer_societe(societe_collectee)
            for changement in changements:
                ajoutee = enregistrer_alertes(
                    siren, [changement],
                    source=getattr(societe_collectee, "source", ""),
                    date_detection=getattr(societe_collectee, "date_collecte", None),
                )
                if (ajoutee and changement.niveau == "critique"
                        and alertes_immediates_actives()):
                    try:
                        envoyer_alerte_critique(
                            siren, getattr(societe_collectee, "raison_sociale", ""),
                            changement,
                        )
                    except ErreurCourriel as erreur:
                        logger.warning(
                            "Alerte immédiate du SIREN %s ignorée : %s", siren, erreur
                        )
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

    if resultats or erreurs_collecte:
        chemin_rapport = generer_rapport(
            resultats, erreurs=erreurs_collecte
        )
        logger.info("Rapport généré : %s", chemin_rapport)
        print()
        print(f"Rapport enregistré dans : {chemin_rapport}")
        try:
            url_notion = publier_rapport_veille(
                chemin_rapport, resultats, erreurs_collecte
            )
            if url_notion:
                logger.info("Rapport publié dans Notion : %s", url_notion)
                print(f"Rapport publié dans Notion : {url_notion}")
        except ErreurNotion as erreur:
            logger.warning("Publication Notion ignorée : %s", erreur)
            print(f"Publication Notion ignorée : {erreur}")

    logger.info("Fin de la veille juridique")
    return chemin_rapport if resultats or erreurs_collecte else None


def executer_hebdomadaire(
    sans_interface: bool = True, source: str = "pappers"
):
    """Exécute la collecte puis la synthèse, strictement dans cet ordre."""
    logger.info("Démarrage de l'exécution hebdomadaire")
    identifiant = demarrer_execution_veille("hebdomadaire", source)
    try:
        executer(sans_interface=sans_interface, source=source)
        chemin_synthese = generer_synthese_hebdomadaire()
    except Exception as erreur:
        terminer_execution_veille(
            identifiant, "echec", message=str(erreur)
        )
        raise
    logger.info("Synthèse hebdomadaire générée : %s", chemin_synthese)
    print(f"Synthèse enregistrée dans : {chemin_synthese}")
    try:
        url_notion = publier_synthese_hebdomadaire(chemin_synthese)
        if url_notion:
            logger.info("Synthèse publiée dans Notion : %s", url_notion)
            print(f"Synthèse publiée dans Notion : {url_notion}")
    except ErreurNotion as erreur:
        logger.warning("Publication de la synthèse Notion ignorée : %s", erreur)
        print(f"Publication Notion ignorée : {erreur}")
    try:
        envoyer_synthese(chemin_synthese)
        logger.info("Synthèse hebdomadaire envoyée par e-mail")
        print("Synthèse envoyée par e-mail.")
    except ErreurCourriel as erreur:
        logger.warning("Envoi de la synthèse ignoré : %s", erreur)
        print(f"Envoi par e-mail ignoré : {erreur}")
    for portefeuille in lire_portefeuilles():
        destinataire = portefeuille.get("destinataire", "").strip()
        if not destinataire:
            continue
        try:
            membres = lire_societes_portefeuille(portefeuille["id"])
            rapport_portefeuille = generer_synthese_portefeuille(
                portefeuille["nom"], [m["siren"] for m in membres]
            )
            envoyer_synthese(
                rapport_portefeuille,
                destinataire=destinataire,
                objet=f"Veille-SIREN — {portefeuille['nom']}",
            )
        except (ErreurCourriel, OSError, ValueError) as erreur:
            enregistrer_envoi_portefeuille(
                portefeuille["id"], destinataire, "echec", str(erreur)
            )
            logger.warning(
                "Envoi du portefeuille %s ignoré : %s",
                portefeuille["nom"], erreur,
            )
        else:
            enregistrer_envoi_portefeuille(
                portefeuille["id"], destinataire, "succes"
            )
    resume = lire_resume_rapport_html(chemin_synthese)
    terminer_execution_veille(
        identifiant,
        "succes",
        societes=resume["societes"],
        modifications=resume["modifications"],
        erreurs=resume["erreurs"],
        rapport=str(chemin_synthese),
    )
    try:
        chemin_sauvegarde = creer_sauvegarde()
        logger.info("Sauvegarde locale créée : %s", chemin_sauvegarde)
        print(f"Sauvegarde créée dans : {chemin_sauvegarde}")
    except ErreurSauvegarde as erreur:
        logger.warning("Sauvegarde locale ignorée : %s", erreur)
        print(f"Sauvegarde ignorée : {erreur}")
    return chemin_synthese


if __name__ == "__main__":
    import argparse

    analyseur = argparse.ArgumentParser()
    analyseur.add_argument(
        "--sauvegarder",
        action="store_true",
        help="Crée immédiatement une sauvegarde locale vérifiée.",
    )
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
    analyseur.add_argument("--siren", action="append", default=[], help="Limite la collecte à un SIREN.")
    analyseur.add_argument(
        "--synthese-hebdomadaire",
        action="store_true",
        help="Génère la synthèse HTML des sept derniers jours sans collecte.",
    )
    analyseur.add_argument(
        "--execution-hebdomadaire",
        action="store_true",
        help="Lance la collecte puis génère la synthèse hebdomadaire.",
    )
    arguments = analyseur.parse_args()
    if arguments.sauvegarder:
        print(f"Sauvegarde créée dans : {creer_sauvegarde()}")
    elif arguments.execution_hebdomadaire:
        executer_hebdomadaire(
            sans_interface=True,
            source=arguments.source,
        )
    elif arguments.synthese_hebdomadaire:
        print(
            "Synthèse enregistrée dans : "
            f"{generer_synthese_hebdomadaire()}"
        )
    else:
        demander_arret_collecte(False)
        executer(
            sans_interface=arguments.sans_interface,
            source=arguments.source,
            sirens=arguments.siren,
        )
