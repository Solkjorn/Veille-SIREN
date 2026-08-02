from collections import defaultdict
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
import re

from config import BASE_SQLITE, DOSSIER_RAPPORTS
from modules.base_donnees import (
    lire_collecte_avant,
    lire_collectes_entre,
    lire_erreurs_taches_entre,
)
from modules.comparaison import detecter_changements
from modules.comparaison import Changement
from modules.modele import Societe


def formater_valeur(valeur: str) -> str:
    """Prépare une valeur pour un tableau Markdown."""
    return (valeur or "—").replace("|", r"\|").replace("\n", " ")


def formater_html(valeur: object) -> str:
    """Protège une valeur avant son insertion dans le rapport HTML."""
    texte = str(valeur).strip() if valeur is not None else ""
    return escape(texte or "—").replace("\n", "<br>")


def lire_resume_rapport_html(chemin: Path) -> dict[str, int]:
    """Extrait les quatre compteurs du bandeau d'un rapport HTML."""
    contenu = Path(chemin).read_text(encoding="utf-8")

    def lire(libelle: str) -> int:
        resultat = re.search(rf"<strong>(\d+)</strong>{re.escape(libelle)}", contenu)
        return int(resultat.group(1)) if resultat else 0

    return {
        "societes": lire("réussies"),
        "modifications": lire("modifiées"),
        "sans_modification": lire("sans changement"),
        "erreurs": lire("erreurs"),
    }


def _nom_base(date_rapport: datetime) -> str:
    return f"veille_{date_rapport.strftime('%Y%m%d_%H%M%S')}"


def nettoyer_rapports_anciens(
    dossier: Path = DOSSIER_RAPPORTS,
    conservation_jours: int = 365,
    maintenant: datetime | None = None,
) -> list[Path]:
    """Supprime uniquement les rapports de veille plus anciens que la limite."""
    if conservation_jours < 1:
        raise ValueError("La durée de conservation doit être positive.")
    dossier = Path(dossier)
    if not dossier.is_dir():
        return []
    limite = (maintenant or datetime.now()) - timedelta(days=conservation_jours)
    supprimes = []
    for chemin in dossier.iterdir():
        nom = chemin.name
        est_rapport_veille = nom.startswith((
            "veille_", "synthese_hebdomadaire_"
        ))
        if (
            chemin.is_file()
            and est_rapport_veille
            and chemin.suffix.casefold() in {".html", ".md"}
            and datetime.fromtimestamp(chemin.stat().st_mtime) < limite
        ):
            chemin.unlink()
            supprimes.append(chemin)
    return supprimes


def generer_rapport_markdown(
    resultats: list[tuple[Societe, list[Changement]]],
    dossier: Path = DOSSIER_RAPPORTS,
    date_rapport: datetime | None = None,
    erreurs: list[tuple[str, str]] | None = None,
) -> Path:
    """Génère le format Markdown secondaire d'un rapport de veille."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    date_rapport = date_rapport or datetime.now()
    chemin = dossier / f"{_nom_base(date_rapport)}.md"
    erreurs = erreurs or []

    lignes = [
        "# Rapport de veille SIREN",
        "",
        f"Généré le {date_rapport.strftime('%d/%m/%Y à %H:%M:%S')}.",
        "",
        f"Collectes réussies : {len(resultats)}.",
        f"Sociétés modifiées : {sum(bool(c) for _, c in resultats)}.",
        f"Erreurs : {len(erreurs)}.",
        "",
    ]
    for societe, changements in resultats:
        lignes.extend(_section_markdown(societe, changements))
    if erreurs:
        lignes.extend(["## Erreurs", ""])
        for siren, message in erreurs:
            lignes.append(f"- **{formater_valeur(siren)}** : {formater_valeur(message)}")
    chemin.write_text("\n".join(lignes), encoding="utf-8")
    return chemin


def _section_markdown(
    societe: Societe, changements: list[Changement]
) -> list[str]:
    lignes = [
        f"## {formater_valeur(societe.raison_sociale)} ({societe.siren})",
        "",
        f"Collectée le {societe.date_collecte.strftime('%d/%m/%Y à %H:%M:%S')} "
        f"via {formater_valeur(societe.source)}.",
        "",
        "| Information | Valeur |",
        "|---|---|",
        f"| Statut | {formater_valeur(societe.statut)} |",
        f"| Forme juridique | {formater_valeur(societe.forme_juridique)} |",
        f"| Capital | {formater_valeur(societe.capital)} |",
        f"| Adresse | {formater_valeur(societe.adresse)} |",
        f"| Dirigeant(s) | {formater_valeur(societe.dirigeant)} |",
        f"| Dernière publication BODACC | {formater_valeur(societe.derniere_publication_bodacc)} |",
        f"| Dernier changement | {formater_valeur(societe.dernier_changement)} |",
        "",
        "### Changements détectés",
        "",
    ]
    if changements:
        lignes.extend([
            "| Niveau | Champ | Ancienne valeur | Nouvelle valeur |",
            "|---|---|---|---|",
        ])
        for changement in changements:
            lignes.append(
                f"| {changement.niveau.capitalize()} | {changement.libelle} "
                f"| {formater_valeur(changement.ancienne_valeur)} "
                f"| {formater_valeur(changement.nouvelle_valeur)} |"
            )
    else:
        lignes.append("Aucun changement détecté.")
    lignes.append("")
    return lignes


def generer_rapport_html(
    resultats: list[tuple[Societe, list[Changement]]],
    dossier: Path = DOSSIER_RAPPORTS,
    date_rapport: datetime | None = None,
    erreurs: list[tuple[str, str]] | None = None,
    titre: str = "Rapport de veille SIREN",
    prefixe: str = "veille",
    introduction: str = "",
) -> Path:
    """Génère un rapport HTML autonome, adapté au web et à l'e-mail."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    date_rapport = date_rapport or datetime.now()
    nom = f"{prefixe}_{date_rapport.strftime('%Y%m%d_%H%M%S')}"
    chemin = dossier / f"{nom}.html"
    erreurs = erreurs or []
    modifies = [(s, c) for s, c in resultats if c]
    sans_changement = [(s, c) for s, c in resultats if not c]

    sections_modifiees = "".join(
        _section_html(societe, changements) for societe, changements in modifies
    ) or '<p class="vide">Aucune société modifiée.</p>'
    sections_stables = "".join(
        _section_html(societe, changements)
        for societe, changements in sans_changement
    ) or '<p class="vide">Aucune société sans changement.</p>'
    section_erreurs = "".join(
        f"<li><strong>{formater_html(siren)}</strong> — {formater_html(message)}</li>"
        for siren, message in erreurs
    ) or "<li>Aucune erreur.</li>"

    contenu = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{formater_html(titre)}</title><style>
body{{margin:0;background:#f3f6f4;color:#16231e;font:15px/1.5 Arial,sans-serif}}
main{{max-width:960px;margin:auto;padding:32px 18px}} header{{padding:28px;background:#087c68;color:white;border-radius:14px}}
h1,h2,h3{{margin-top:0}} .resume{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}}
.resume div,.societe,.erreurs{{padding:18px;background:white;border:1px solid #d9e2dd;border-radius:12px}}
.resume strong{{display:block;font-size:26px;color:#087c68}} .societe{{margin:14px 0}}
.meta,.vide{{color:#5d6d66}} table{{width:100%;border-collapse:collapse;margin-top:14px}}
th,td{{padding:10px;border-bottom:1px solid #e1e7e3;text-align:left;vertical-align:top}}
th{{color:#53645d;font-size:12px;text-transform:uppercase}} .avant{{color:#9b332b}} .apres{{color:#087c68;font-weight:bold}}
.niveau{{font-weight:bold}} .niveau-critique{{color:#a32222}} .niveau-important{{color:#9a5b00}} .niveau-informatif{{color:#42675b}}
@media(max-width:650px){{.resume{{grid-template-columns:1fr 1fr}} table{{font-size:13px}}}}
</style></head><body><main>
<header><h1>{formater_html(titre)}</h1><p>Généré le {date_rapport.strftime('%d/%m/%Y à %H:%M:%S')}</p><p>{formater_html(introduction) if introduction else ''}</p></header>
<section class="resume" aria-label="Résumé"><div><strong>{len(resultats)}</strong>réussies</div>
<div><strong>{len(modifies)}</strong>modifiées</div><div><strong>{len(sans_changement)}</strong>sans changement</div>
<div><strong>{len(erreurs)}</strong>erreurs</div></section>
<section><h2>Sociétés modifiées</h2>{sections_modifiees}</section>
<section><h2>Sociétés sans changement</h2>{sections_stables}</section>
<section class="erreurs"><h2>Erreurs de collecte</h2><ul>{section_erreurs}</ul></section>
</main></body></html>"""
    chemin.write_text(contenu, encoding="utf-8")
    return chemin


def _section_html(societe: Societe, changements: list[Changement]) -> str:
    informations = (
        ("Forme juridique", societe.forme_juridique),
        ("Capital", societe.capital),
        ("Adresse", societe.adresse),
        ("Dirigeant(s)", societe.dirigeant),
        ("Dernière publication BODACC", societe.derniere_publication_bodacc),
        ("Dernier changement", societe.dernier_changement),
    )
    lignes_informations = "".join(
        f"<tr><td>{formater_html(libelle)}</td><td>{formater_html(valeur)}</td></tr>"
        for libelle, valeur in informations
    )
    lignes_changements = "".join(
        f"<tr><td class=\"niveau niveau-{c.niveau}\">{formater_html(c.niveau.capitalize())}</td>"
        f"<td>{formater_html(c.libelle)}</td><td class=\"avant\">{formater_html(c.ancienne_valeur)}</td>"
        f"<td class=\"apres\">{formater_html(c.nouvelle_valeur)}</td></tr>"
        for c in changements
    )
    changements_html = (
        f"<table><thead><tr><th>Niveau</th><th>Champ</th><th>Ancienne valeur</th><th>Nouvelle valeur</th></tr></thead>"
        f"<tbody>{lignes_changements}</tbody></table>"
        if changements else '<p class="vide">Aucun changement détecté.</p>'
    )
    return f"""<article class="societe"><h3>{formater_html(societe.raison_sociale)} ({formater_html(societe.siren)})</h3>
<p class="meta">Collectée le {societe.date_collecte.strftime('%d/%m/%Y à %H:%M:%S')} · Source : {formater_html(societe.source)} · État : {formater_html(societe.statut)}</p>
<table><thead><tr><th>Information</th><th>Valeur collectée</th></tr></thead><tbody>{lignes_informations}</tbody></table>
<h4>Changements détectés</h4>
{changements_html}</article>"""


def generer_rapport(
    resultats: list[tuple[Societe, list[Changement]]],
    dossier: Path = DOSSIER_RAPPORTS,
    date_rapport: datetime | None = None,
    erreurs: list[tuple[str, str]] | None = None,
) -> Path:
    """Génère le HTML principal et conserve un Markdown secondaire."""
    date_rapport = date_rapport or datetime.now()
    generer_rapport_markdown(resultats, dossier, date_rapport, erreurs)
    chemin = generer_rapport_html(resultats, dossier, date_rapport, erreurs)
    nettoyer_rapports_anciens(dossier)
    return chemin


def generer_synthese_hebdomadaire(
    chemin_base: Path = BASE_SQLITE,
    dossier: Path = DOSSIER_RAPPORTS,
    date_fin: datetime | None = None,
) -> Path:
    """Crée une synthèse des sept derniers jours depuis l'historique SQLite."""
    date_fin = date_fin or datetime.now()
    date_debut = date_fin - timedelta(days=7)
    collectes = lire_collectes_entre(date_debut, date_fin, chemin_base)
    erreurs = lire_erreurs_taches_entre(date_debut, date_fin, chemin_base)
    par_siren: dict[str, list[Societe]] = defaultdict(list)
    for collecte in collectes:
        par_siren[collecte.siren].append(collecte)

    resultats = []
    for siren, historique in par_siren.items():
        precedente = lire_collecte_avant(siren, date_debut, chemin_base)
        reference = precedente or historique[0]
        derniere = historique[-1]
        changements = (
            detecter_changements(reference, derniere)
            if reference is not derniere else []
        )
        resultats.append((derniere, changements))

    resultats.sort(key=lambda element: element[0].raison_sociale or element[0].siren)
    chemin = generer_rapport_html(
        resultats,
        dossier=dossier,
        date_rapport=date_fin,
        titre="Synthèse hebdomadaire Veille-SIREN",
        prefixe="synthese_hebdomadaire",
        introduction=(
            f"Période du {date_debut.strftime('%d/%m/%Y %H:%M')} "
            f"au {date_fin.strftime('%d/%m/%Y %H:%M')}"
        ),
        erreurs=erreurs,
    )
    nettoyer_rapports_anciens(dossier)
    return chemin


def generer_synthese_portefeuille(
    nom: str,
    sirens: list[str],
    chemin_base: Path = BASE_SQLITE,
    dossier: Path = DOSSIER_RAPPORTS,
    date_fin: datetime | None = None,
) -> Path:
    """Crée une synthèse hebdomadaire limitée à un portefeuille."""
    date_fin = date_fin or datetime.now()
    date_debut = date_fin - timedelta(days=7)
    sirens = {str(siren).strip() for siren in sirens}
    collectes = [
        collecte for collecte in lire_collectes_entre(
            date_debut, date_fin, chemin_base
        ) if collecte.siren in sirens
    ]
    erreurs = [
        erreur for erreur in lire_erreurs_taches_entre(
            date_debut, date_fin, chemin_base
        ) if erreur[0] in sirens
    ]
    par_siren: dict[str, list[Societe]] = defaultdict(list)
    for collecte in collectes:
        par_siren[collecte.siren].append(collecte)
    resultats = []
    for siren, historique in par_siren.items():
        precedente = lire_collecte_avant(siren, date_debut, chemin_base)
        reference, derniere = precedente or historique[0], historique[-1]
        changements = (
            detecter_changements(reference, derniere)
            if reference is not derniere else []
        )
        resultats.append((derniere, changements))
    nom_fichier = re.sub(r"[^a-z0-9]+", "_", nom.casefold()).strip("_")
    return generer_rapport_html(
        sorted(resultats, key=lambda x: x[0].raison_sociale or x[0].siren),
        dossier=dossier, date_rapport=date_fin, erreurs=erreurs,
        titre=f"Synthèse hebdomadaire — {nom}",
        prefixe=f"portefeuille_{nom_fichier or 'sans_nom'}",
        introduction=(
            f"Portefeuille {nom} · période du "
            f"{date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}"
        ),
    )
