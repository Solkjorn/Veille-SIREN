import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ErreurAPI(ConnectionError):
    pass


def requete_json(
    url: str,
    entetes: dict[str, str] | None = None,
    donnees: dict | None = None,
    delai: int = 30,
) -> dict:
    """Exécute une requête JSON sans dépendance HTTP supplémentaire."""
    corps = None
    headers = {"Accept": "application/json", **(entetes or {})}
    methode = "GET"
    if donnees is not None:
        corps = json.dumps(donnees).encode("utf-8")
        headers["Content-Type"] = "application/json"
        methode = "POST"
    requete = Request(url, data=corps, headers=headers, method=methode)
    try:
        with urlopen(requete, timeout=delai) as reponse:
            return json.loads(reponse.read().decode("utf-8"))
    except HTTPError as erreur:
        raise ErreurAPI(f"API HTTP {erreur.code} pour {url}") from erreur
    except (URLError, TimeoutError, json.JSONDecodeError) as erreur:
        raise ErreurAPI(f"API indisponible pour {url}: {erreur}") from erreur
