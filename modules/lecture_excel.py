from modules.import_excel import analyser_fichier_excel


def lire_sirens(fichier_excel):
    """
    Lit et valide les SIREN du fichier Excel.

    Cette fonction historique conserve son format de retour. Les nouveaux
    usages peuvent appeler ``analyser_fichier_excel`` pour obtenir le détail
    des erreurs avant l'import.
    """
    apercu = analyser_fichier_excel(fichier_excel)
    if apercu.erreurs:
        details = "; ".join(
            f"ligne {erreur.numero} : {erreur.message}"
            for erreur in apercu.erreurs
        )
        raise ValueError(f"Fichier Excel invalide : {details}")
    return [
        {
            "siren": ligne.siren,
            "actif": ligne.actif,
            "commentaire": ligne.commentaire,
        }
        for ligne in apercu.lignes
    ]
