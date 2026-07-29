from datetime import datetime
from pathlib import Path

from config import DOSSIER_RAPPORTS
from modules.comparaison import Changement
from modules.modele import Societe


def formater_valeur(valeur: str) -> str:
    """
    Prépare une valeur pour son insertion dans un tableau Markdown.
    """
    return (valeur or "—").replace("|", r"\|").replace("\n", " ")


def generer_rapport(
    resultats: list[tuple[Societe, list[Changement]]],
    dossier: Path = DOSSIER_RAPPORTS,
    date_rapport: datetime | None = None,
) -> Path:
    """
    Génère un rapport Markdown pour une exécution de la veille.
    """
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    date_rapport = date_rapport or datetime.now()
    chemin = dossier / (
        f"veille_{date_rapport.strftime('%Y%m%d_%H%M%S')}.md"
    )

    lignes = [
        "# Rapport de veille SIREN",
        "",
        f"Généré le {date_rapport.strftime('%d/%m/%Y à %H:%M:%S')}.",
        "",
        f"Nombre de sociétés collectées : {len(resultats)}.",
        "",
    ]

    for societe, changements in resultats:
        lignes.extend(
            [
                f"## {formater_valeur(societe.raison_sociale)} "
                f"({societe.siren})",
                "",
                "| Information | Valeur |",
                "|---|---|",
                f"| Statut | {formater_valeur(societe.statut)} |",
                (
                    "| Forme juridique | "
                    f"{formater_valeur(societe.forme_juridique)} |"
                ),
                f"| Capital | {formater_valeur(societe.capital)} |",
                f"| Adresse | {formater_valeur(societe.adresse)} |",
                f"| Dirigeant(s) | {formater_valeur(societe.dirigeant)} |",
                (
                    "| Dernière publication BODACC | "
                    f"{formater_valeur(societe.derniere_publication_bodacc)} |"
                ),
                (
                    "| Dernier changement | "
                    f"{formater_valeur(societe.dernier_changement)} |"
                ),
                "",
                "### Changements détectés",
                "",
            ]
        )

        if changements:
            lignes.extend(
                [
                    "| Champ | Ancienne valeur | Nouvelle valeur |",
                    "|---|---|---|",
                ]
            )

            for changement in changements:
                lignes.append(
                    f"| {changement.libelle} "
                    f"| {formater_valeur(changement.ancienne_valeur)} "
                    f"| {formater_valeur(changement.nouvelle_valeur)} |"
                )
        else:
            lignes.append("Aucun changement détecté.")

        lignes.append("")

    chemin.write_text("\n".join(lignes), encoding="utf-8")
    return chemin
