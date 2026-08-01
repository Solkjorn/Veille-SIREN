import json
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
