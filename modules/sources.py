import os
from urllib.parse import quote, urlencode

from playwright.sync_api import Page

from modules.client_http import ErreurAPI, requete_json
from modules.modele import Societe
from modules.pappers import lire_pappers_avec_page
from modules.secrets_windows import lire_cle_insee


class ConfigurationSourceInvalide(RuntimeError):
    pass


class SourcePappers:
    nom = "Pappers"
    necessite_navigateur = True

    def collecter(self, siren: str, page: Page | None = None) -> Societe:
        if page is None:
            raise RuntimeError("Pappers nécessite une page de navigateur.")
        return lire_pappers_avec_page(siren, page)


class SourceINSEE:
    nom = "INSEE"
    necessite_navigateur = False
    url_base = "https://api.insee.fr/api-sirene/3.11/siren"

    def __init__(self, cle_api: str | None = None):
        self.cle_api = (
            cle_api
            or os.getenv("VEILLE_SIREN_INSEE_API_KEY", "")
            or lire_cle_insee()
        )

    def collecter(self, siren: str, page: Page | None = None) -> Societe:
        if not self.cle_api:
            raise ConfigurationSourceInvalide(
                "INSEE requiert une clé API dans le coffre Windows ou "
                "VEILLE_SIREN_INSEE_API_KEY."
            )
        entetes = {"X-INSEE-Api-Key-Integration": self.cle_api}
        donnees = requete_json(f"{self.url_base}/{quote(siren)}", entetes)
        unite = donnees.get("uniteLegale", donnees)
        periodes = unite.get("periodesUniteLegale") or [{}]
        periode = periodes[0]
        denomination = periode.get("denominationUniteLegale", "")
        if not denomination:
            denomination = " ".join(
                valeur for valeur in (
                    unite.get("prenomUsuelUniteLegale", ""),
                    unite.get("nomUniteLegale", ""),
                ) if valeur
            )
        statut = {
            "A": "Active",
            "C": "Cessée",
        }.get(periode.get("etatAdministratifUniteLegale", ""), "")
        return Societe(
            siren=siren,
            raison_sociale=denomination,
            forme_juridique=periode.get("categorieJuridiqueUniteLegale", ""),
            statut=statut,
            source=self.nom,
        )


class SourceINPI:
    nom = "INPI"
    necessite_navigateur = False
    url_base = "https://registre-national-entreprises.inpi.fr/api"

    def __init__(
        self,
        identifiant: str | None = None,
        mot_de_passe: str | None = None,
    ):
        self.identifiant = identifiant or os.getenv("VEILLE_SIREN_INPI_USER", "")
        self.mot_de_passe = mot_de_passe or os.getenv(
            "VEILLE_SIREN_INPI_PASSWORD", ""
        )
        self._jeton = ""

    def _authentifier(self) -> str:
        if not self.identifiant or not self.mot_de_passe:
            raise ConfigurationSourceInvalide(
                "INPI requiert VEILLE_SIREN_INPI_USER et "
                "VEILLE_SIREN_INPI_PASSWORD."
            )
        reponse = requete_json(
            f"{self.url_base}/sso/login",
            donnees={
                "username": self.identifiant,
                "password": self.mot_de_passe,
            },
        )
        self._jeton = reponse.get("token", "")
        if not self._jeton:
            raise ErreurAPI("L'authentification INPI n'a renvoyé aucun jeton.")
        return self._jeton

    def collecter(self, siren: str, page: Page | None = None) -> Societe:
        jeton = self._jeton or self._authentifier()
        donnees = requete_json(
            f"{self.url_base}/companies/{quote(siren)}",
            {"Authorization": f"Bearer {jeton}"},
        )
        contenu = donnees.get("content", donnees)
        identite = contenu.get("personneMorale", {}).get("identite", {})
        entreprise = identite.get("entreprise", identite)
        denomination = entreprise.get("denomination", "")
        forme = entreprise.get("formeJuridique", "")
        return Societe(
            siren=siren,
            raison_sociale=denomination,
            forme_juridique=str(forme),
            source=self.nom,
        )


class SourceBODACC:
    nom = "BODACC"
    necessite_navigateur = False
    url = (
        "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/"
        "datasets/annonces-commerciales/records"
    )

    def collecter(self, siren: str, page: Page | None = None) -> Societe:
        parametres = urlencode({
            "where": f'search(registre, "{siren}")',
            "order_by": "dateparution DESC",
            "limit": 1,
        })
        donnees = requete_json(f"{self.url}?{parametres}")
        resultats = donnees.get("results", [])
        annonce = resultats[0] if resultats else {}
        objet = (
            annonce.get("typeavis")
            or annonce.get("familleavis_lib")
            or annonce.get("typeannonce")
            or ""
        )
        detail = (
            annonce.get("modificationsgenerales")
            or annonce.get("jugement")
            or annonce.get("descriptif")
            or ""
        )
        changement = " — ".join(x for x in (objet, detail) if x)
        return Societe(
            siren=siren,
            raison_sociale=annonce.get("commercant", ""),
            derniere_publication_bodacc=annonce.get("dateparution", ""),
            dernier_changement=changement,
            source=self.nom,
        )


SOURCES_DISPONIBLES = {
    "pappers": SourcePappers,
    "insee": SourceINSEE,
    "inpi": SourceINPI,
    "bodacc": SourceBODACC,
}


def creer_source(nom: str):
    try:
        return SOURCES_DISPONIBLES[nom.casefold()]()
    except KeyError as erreur:
        choix = ", ".join(SOURCES_DISPONIBLES)
        raise ValueError(f"Source inconnue : {nom}. Choix : {choix}") from erreur
