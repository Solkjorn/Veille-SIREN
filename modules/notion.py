import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config import BASE_SQLITE
from modules.base_donnees import (
    enregistrer_publication_notion,
    lire_cible_notion,
    publication_notion_existe,
)
from modules.secrets_windows import lire_jeton_notion


API_NOTION = "https://api.notion.com/v1"
VERSION_NOTION = "2026-03-11"


class ErreurNotion(RuntimeError):
    """Erreur lisible produite par la publication Notion."""


def normaliser_identifiant_notion(identifiant: str) -> str:
    """Retire les préfixes utilisés par les connecteurs autour des UUID."""
    valeur = str(identifiant).strip()
    for prefixe in ("collection://", "data_source://"):
        if valeur.startswith(prefixe):
            return valeur.removeprefix(prefixe)
    return valeur


def _texte(contenu: str) -> list[dict]:
    return [{"type": "text", "text": {"content": str(contenu)[:2000]}}]


def _bloc_paragraphe(contenu: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": _texte(contenu)},
    }


def _blocs_depuis_markdown(contenu: str) -> list[dict]:
    """Convertit le Markdown courant des rapports en blocs Notion simples."""
    blocs = []
    paragraphe = []

    def vider_paragraphe() -> None:
        if paragraphe:
            blocs.append(_bloc_paragraphe(" ".join(paragraphe)))
            paragraphe.clear()

    for ligne in contenu.splitlines():
        ligne = ligne.strip()
        if not ligne:
            vider_paragraphe()
            continue
        correspondance = re.match(r"^(#{1,3})\s+(.+)$", ligne)
        if correspondance:
            vider_paragraphe()
            niveau = len(correspondance.group(1))
            type_bloc = f"heading_{niveau}"
            blocs.append({
                "object": "block",
                "type": type_bloc,
                type_bloc: {"rich_text": _texte(correspondance.group(2))},
            })
        elif ligne.startswith("- "):
            vider_paragraphe()
            blocs.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": _texte(ligne[2:])},
            })
        else:
            paragraphe.append(ligne)
    vider_paragraphe()
    return blocs[:100]


def _appel_api(
    methode: str,
    route: str,
    jeton: str,
    donnees: dict | None = None,
    ouvre=urlopen,
) -> dict:
    corps = json.dumps(donnees).encode("utf-8") if donnees is not None else None
    requete = Request(
        f"{API_NOTION}{route}",
        data=corps,
        method=methode,
        headers={
            "Authorization": f"Bearer {jeton}",
            "Notion-Version": VERSION_NOTION,
            "Content-Type": "application/json",
        },
    )
    try:
        with ouvre(requete, timeout=30) as reponse:
            return json.loads(reponse.read().decode("utf-8"))
    except HTTPError as erreur:
        detail = erreur.read().decode("utf-8", errors="replace")
        try:
            message = json.loads(detail).get("message", detail)
        except json.JSONDecodeError:
            message = detail
        raise ErreurNotion(f"Notion HTTP {erreur.code} : {message}") from erreur
    except (URLError, TimeoutError, OSError) as erreur:
        raise ErreurNotion(f"Notion est indisponible : {erreur}") from erreur


def verifier_connexion_notion(jeton: str | None = None, ouvre=urlopen) -> dict:
    """Vérifie le jeton en récupérant l'utilisateur qui lui est associé."""
    jeton = (jeton or lire_jeton_notion()).strip()
    if not jeton:
        raise ErreurNotion("Aucun jeton Notion n'est configuré.")
    return _appel_api("GET", "/users/me", jeton, ouvre=ouvre)


def publier_rapport_veille(
    chemin_rapport: Path,
    resultats: list,
    erreurs: list[tuple[str, str]] | None = None,
    chemin_base: Path = BASE_SQLITE,
    jeton: str | None = None,
    ouvre=urlopen,
) -> str | None:
    """Publie un rapport quotidien, une seule fois, dans la cible Notion."""
    chemin_rapport = Path(chemin_rapport)
    identifiant = chemin_rapport.stem
    if publication_notion_existe(identifiant, chemin_base):
        return None

    jeton = (jeton or lire_jeton_notion()).strip()
    cible = normaliser_identifiant_notion(
        lire_cible_notion("rapports_veille", chemin_base)
    )
    if not jeton:
        raise ErreurNotion("Aucun jeton Notion n'est configuré.")
    if not cible:
        raise ErreurNotion("La cible Notion des rapports de veille est absente.")

    erreurs = erreurs or []
    modifies = sum(bool(changements) for _, changements in resultats)
    date_rapport = datetime.fromtimestamp(chemin_rapport.stat().st_mtime)
    titre = f"Rapport de veille — {date_rapport.strftime('%d/%m/%Y %H:%M')}"
    donnees = {
        "parent": {"type": "data_source_id", "data_source_id": cible},
        "properties": {
            "Rapport": {"title": _texte(titre)},
            "Date": {"date": {"start": date_rapport.isoformat(timespec="seconds")}},
            "Type": {"select": {"name": "Quotidien"}},
            "Statut": {"select": {"name": "Publié"}},
            "Identifiant": {"rich_text": _texte(identifiant)},
            "Sociétés": {"number": len(resultats)},
            "Modifications": {"number": modifies},
            "Erreurs": {"number": len(erreurs)},
            "Fichier": {"rich_text": _texte(chemin_rapport.name)},
        },
        "children": [
            _bloc_paragraphe(
                f"{len(resultats)} collecte(s) réussie(s), {modifies} société(s) "
                f"modifiée(s) et {len(erreurs)} erreur(s)."
            ),
            _bloc_paragraphe(
                "Le rapport HTML complet reste consultable depuis l'interface "
                f"Veille-SIREN : {chemin_rapport.name}."
            ),
        ],
    }
    page = _appel_api("POST", "/pages", jeton, donnees, ouvre)
    page_id, url = page.get("id", ""), page.get("url", "")
    if not page_id or not url:
        raise ErreurNotion("La réponse Notion ne contient ni page ni URL valide.")
    enregistrer_publication_notion(identifiant, page_id, url, chemin_base)
    return url


def publier_rapport_developpement(
    chemin_rapport: Path,
    chemin_base: Path = BASE_SQLITE,
    jeton: str | None = None,
    ouvre=urlopen,
) -> str | None:
    """Publie un compte rendu de développement dans le Journal de travail."""
    chemin_rapport = Path(chemin_rapport)
    correspondance = re.fullmatch(
        r"developpement_(\d{4})(\d{2})(\d{2})\.md", chemin_rapport.name
    )
    if not correspondance:
        raise ValueError(
            "Le rapport doit respecter le nom developpement_YYYYMMDD.md."
        )
    identifiant = chemin_rapport.stem
    if publication_notion_existe(identifiant, chemin_base):
        return None

    jeton = (jeton or lire_jeton_notion()).strip()
    cible = normaliser_identifiant_notion(
        lire_cible_notion("rapports_developpement", chemin_base)
    )
    if not jeton:
        raise ErreurNotion("Aucun jeton Notion n'est configuré.")
    if not cible:
        raise ErreurNotion("La cible Notion des rapports de développement est absente.")
    if not chemin_rapport.is_file():
        raise FileNotFoundError(chemin_rapport)

    annee, mois, jour = map(int, correspondance.groups())
    date_rapport = datetime(annee, mois, jour)
    contenu = chemin_rapport.read_text(encoding="utf-8")
    lignes = contenu.splitlines()
    if lignes and lignes[0].startswith("# "):
        contenu = "\n".join(lignes[1:]).lstrip()
    mois_francais = (
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    )
    titre = f"Compte rendu — {jour} {mois_francais[mois - 1]} {annee}"
    donnees = {
        "parent": {"type": "data_source_id", "data_source_id": cible},
        "properties": {
            "Compte rendu": {"title": _texte(titre)},
            "Date": {"date": {"start": date_rapport.strftime("%Y-%m-%d")}},
            "Statut": {"select": {"name": "Publié"}},
        },
        "children": _blocs_depuis_markdown(contenu),
    }
    page = _appel_api("POST", "/pages", jeton, donnees, ouvre)
    page_id, url = page.get("id", ""), page.get("url", "")
    if not page_id or not url:
        raise ErreurNotion("La réponse Notion ne contient ni page ni URL valide.")
    enregistrer_publication_notion(identifiant, page_id, url, chemin_base)
    return url


def publier_synthese_hebdomadaire(
    chemin_rapport: Path,
    chemin_base: Path = BASE_SQLITE,
    jeton: str | None = None,
    ouvre=urlopen,
) -> str | None:
    """Publie une synthèse HTML hebdomadaire dans la base des rapports."""
    chemin_rapport = Path(chemin_rapport)
    identifiant = chemin_rapport.stem
    if not identifiant.startswith("synthese_hebdomadaire_"):
        raise ValueError("Le fichier n'est pas une synthèse hebdomadaire reconnue.")
    if publication_notion_existe(identifiant, chemin_base):
        return None

    jeton = (jeton or lire_jeton_notion()).strip()
    cible = normaliser_identifiant_notion(
        lire_cible_notion("rapports_veille", chemin_base)
    )
    if not jeton:
        raise ErreurNotion("Aucun jeton Notion n'est configuré.")
    if not cible:
        raise ErreurNotion("La cible Notion des rapports de veille est absente.")
    contenu = chemin_rapport.read_text(encoding="utf-8")

    def nombre_apres(libelle: str) -> int:
        motif = rf"<strong>(\d+)</strong>{re.escape(libelle)}"
        correspondance = re.search(motif, contenu)
        return int(correspondance.group(1)) if correspondance else 0

    societes = nombre_apres("réussies")
    modifications = nombre_apres("modifiées")
    erreurs = nombre_apres("erreurs")
    date_rapport = datetime.fromtimestamp(chemin_rapport.stat().st_mtime)
    titre = f"Synthèse hebdomadaire — {date_rapport.strftime('%d/%m/%Y %H:%M')}"
    donnees = {
        "parent": {"type": "data_source_id", "data_source_id": cible},
        "properties": {
            "Rapport": {"title": _texte(titre)},
            "Date": {"date": {"start": date_rapport.isoformat(timespec="seconds")}},
            "Type": {"select": {"name": "Hebdomadaire"}},
            "Statut": {"select": {"name": "Publié"}},
            "Identifiant": {"rich_text": _texte(identifiant)},
            "Sociétés": {"number": societes},
            "Modifications": {"number": modifications},
            "Erreurs": {"number": erreurs},
            "Fichier": {"rich_text": _texte(chemin_rapport.name)},
        },
        "children": [_bloc_paragraphe(
            f"{societes} société(s), {modifications} modification(s) et "
            f"{erreurs} erreur(s) sur la période hebdomadaire."
        )],
    }
    page = _appel_api("POST", "/pages", jeton, donnees, ouvre)
    page_id, url = page.get("id", ""), page.get("url", "")
    if not page_id or not url:
        raise ErreurNotion("La réponse Notion ne contient ni page ni URL valide.")
    enregistrer_publication_notion(identifiant, page_id, url, chemin_base)
    return url


def _commande() -> int:
    import argparse

    analyseur = argparse.ArgumentParser()
    analyseur.add_argument(
        "--rapport-developpement", type=Path,
        help="Publie un fichier developpement_YYYYMMDD.md dans Notion.",
    )
    arguments = analyseur.parse_args()
    if not arguments.rapport_developpement:
        analyseur.print_help()
        return 0
    try:
        url = publier_rapport_developpement(arguments.rapport_developpement)
    except (ErreurNotion, FileNotFoundError, ValueError) as erreur:
        print(f"Échec de la publication Notion : {erreur}", file=sys.stderr)
        return 1
    print(url and f"Rapport publié dans Notion : {url}" or "Rapport déjà publié.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_commande())
