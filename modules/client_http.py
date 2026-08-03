import json
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import truststore


CONTEXTE_TLS = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


class ErreurAPI(ConnectionError):
    def __init__(self, message: str, *, temporaire: bool = True):
        super().__init__(message)
        self.temporaire = temporaire


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
        with urlopen(requete, timeout=delai, context=CONTEXTE_TLS) as reponse:
            return json.loads(reponse.read().decode("utf-8"))
    except HTTPError as erreur:
        temporaire = erreur.code in {408, 425, 429} or erreur.code >= 500
        raise ErreurAPI(
            f"API HTTP {erreur.code} pour {url}", temporaire=temporaire
        ) from erreur
    except (URLError, TimeoutError, json.JSONDecodeError) as erreur:
        raise ErreurAPI(f"API indisponible pour {url}: {erreur}") from erreur


def requete_binaire(
    url: str, entetes: dict[str, str] | None = None, delai: int = 30
) -> tuple[bytes, str]:
    """Télécharge un contenu binaire et retourne aussi son type MIME."""
    requete = Request(url, headers=entetes or {}, method="GET")
    try:
        with urlopen(requete, timeout=delai, context=CONTEXTE_TLS) as reponse:
            return reponse.read(), reponse.headers.get_content_type()
    except HTTPError as erreur:
        temporaire = erreur.code in {408, 425, 429} or erreur.code >= 500
        raise ErreurAPI(
            f"API HTTP {erreur.code} pour {url}", temporaire=temporaire
        ) from erreur
    except (URLError, TimeoutError) as erreur:
        raise ErreurAPI(f"API indisponible pour {url}: {erreur}") from erreur
