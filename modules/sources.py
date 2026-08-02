import json
import os
import re
import time
from datetime import date, datetime
from urllib.parse import quote, urlencode

from playwright.sync_api import Page

from modules.client_http import ErreurAPI, requete_binaire, requete_json
from modules.modele import Societe
from modules.pappers import lire_pappers_avec_page
from modules.secrets_windows import lire_cle_insee, lire_identifiants_inpi


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
        identifiant_coffre, mot_de_passe_coffre = lire_identifiants_inpi()
        self.identifiant = (
            identifiant
            or os.getenv("VEILLE_SIREN_INPI_USER", "")
            or identifiant_coffre
        )
        self.mot_de_passe = (
            mot_de_passe
            or os.getenv("VEILLE_SIREN_INPI_PASSWORD", "")
            or mot_de_passe_coffre
        )
        self._jeton = ""

    def _authentifier(self) -> str:
        if not self.identifiant or not self.mot_de_passe:
            raise ConfigurationSourceInvalide(
                "INPI requiert des identifiants dans le coffre Windows ou "
                "VEILLE_SIREN_INPI_USER et VEILLE_SIREN_INPI_PASSWORD."
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
        formalite = donnees.get("formality", donnees)
        contenu = formalite.get("content", formalite)
        identite = contenu.get("personneMorale", {}).get("identite", {})
        entreprise = identite.get("entreprise", identite)
        denomination = entreprise.get("denomination", "")
        forme = entreprise.get("formeJuridique", "")
        pieces = requete_json(
            f"{self.url_base}/companies/{quote(siren)}/attachments",
            {"Authorization": f"Bearer {jeton}"},
        )
        documents = []
        for type_document, cle in (
            ("acte", "actes"), ("bilan", "bilans"),
            ("bilan_saisi", "bilansSaisis"),
        ):
            for document in pieces.get(cle, []) or []:
                if document.get("id") and not document.get("deleted", False):
                    documents.append({
                        "identifiant": str(document["id"]),
                        "type_document": type_document,
                        "date_depot": str(document.get("dateDepot", "")),
                        "date_mise_a_jour": str(document.get("updatedAt", "")),
                        "libelle": str(
                            document.get("libelle")
                            or document.get("typeDocument")
                            or document.get("typeBilan") or "Document INPI"
                        ),
                        "nom_document": str(document.get("nomDocument", "")),
                        "confidentialite": str(document.get("confidentiality", "")),
                    })
        return Societe(
            siren=siren,
            raison_sociale=denomination,
            forme_juridique=str(forme),
            source=self.nom,
            documents_inpi=documents,
        )

    def telecharger_document(self, type_document: str, identifiant: str):
        """Télécharge un document autorisé uniquement à la demande."""
        routes = {"acte": "actes", "bilan": "bilans", "bilan_saisi": "bilans-saisis"}
        try:
            route = routes[type_document]
        except KeyError as erreur:
            raise ValueError("Type de document INPI inconnu.") from erreur
        jeton = self._jeton or self._authentifier()
        return requete_binaire(
            f"{self.url_base}/{route}/{quote(identifiant, safe='')}/download",
            {"Authorization": f"Bearer {jeton}"},
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
            annonce.get("familleavis_lib")
            or annonce.get("typeannonce")
            or annonce.get("typeavis_lib")
            or annonce.get("typeavis")
            or ""
        )
        detail = (
            annonce.get("modificationsgenerales")
            or annonce.get("jugement")
            or annonce.get("depot")
            or annonce.get("descriptif")
            or ""
        )
        if isinstance(detail, str) and detail.lstrip().startswith("{"):
            try:
                detail = json.loads(detail)
            except json.JSONDecodeError:
                pass
        if isinstance(detail, dict):
            detail = " — ".join(
                str(detail.get(cle, "")).strip()
                for cle in ("typeDepot", "dateCloture", "nature", "descriptif")
                if str(detail.get(cle, "")).strip()
            )
        changement = " — ".join(x for x in (objet, detail) if x)
        return Societe(
            siren=siren,
            raison_sociale=annonce.get("commercant", ""),
            derniere_publication_bodacc=annonce.get("dateparution", ""),
            dernier_changement=changement,
            source=self.nom,
        )


class ErreurCollecteMultisource(RuntimeError):
    pass


PRIORITES_CHAMPS = {
    "raison_sociale": ("INSEE", "INPI", "BODACC", "Pappers"),
    "forme_juridique": ("Pappers", "INPI", "INSEE"),
    "capital": ("Pappers",),
    "statut": ("INSEE", "Pappers"),
    "adresse": ("Pappers", "INPI"),
    "dirigeant": ("INPI", "Pappers"),
    "derniere_publication_bodacc": ("BODACC", "Pappers"),
    "dernier_changement": ("BODACC", "Pappers"),
}


def _normaliser_comparaison(champ: str, valeur: str) -> str:
    valeur = " ".join(valeur.casefold().split())
    if champ == "derniere_publication_bodacc":
        for format_date in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(valeur, format_date).date().isoformat()
            except ValueError:
                pass
    valeur = re.sub(r"[^a-z0-9à-ÿ]+", " ", valeur).strip()
    if champ == "dernier_changement":
        valeur = valeur.replace("dépôts", "dépôt").replace("depots", "depot")
    return valeur


def _valeurs_contradictoires(champ: str, valeurs: dict[str, str]) -> bool:
    normalisees = {_normaliser_comparaison(champ, valeur) for valeur in valeurs.values()}
    if len(normalisees) <= 1:
        return False
    if champ == "forme_juridique":
        numeriques = {valeur for valeur in normalisees if valeur.isdigit()}
        textuelles = normalisees - numeriques
        if len(numeriques) <= 1 and len(textuelles) <= 1:
            return False
    if champ == "dernier_changement":
        ordonnees = sorted(normalisees, key=len)
        if ordonnees and all(ordonnees[0] in valeur for valeur in ordonnees[1:]):
            return False
    return True


class SourceMultisource:
    """Fusionne plusieurs sources selon des priorités explicites par champ."""

    nom = "Multisource"

    CHAMPS_ESSENTIELS = (
        "raison_sociale", "forme_juridique", "statut",
        "derniere_publication_bodacc",
    )

    def __init__(
        self,
        sources=None,
        forcer_pappers: bool | None = None,
        date_reference: date | None = None,
        tentatives_sources: int = 3,
        delai_initial: float = 1.0,
        pause=time.sleep,
    ):
        if tentatives_sources < 1 or delai_initial < 0:
            raise ValueError("La politique de reprise multisource est invalide.")
        self.sources = sources or [
            SourceINSEE(), SourceINPI(), SourceBODACC(), SourcePappers(),
        ]
        date_reference = date_reference or date.today()
        self.forcer_pappers = (
            date_reference.day <= 7
            if forcer_pappers is None
            else bool(forcer_pappers)
        )
        self.tentatives_sources = tentatives_sources
        self.delai_initial = delai_initial
        self.pause = pause
        self.necessite_navigateur = any(
            source.necessite_navigateur for source in self.sources
        )
        self.erreurs_sources = {}
        self.provenance = {}
        self.contradictions = {}

    def _collecter_source(self, source, siren: str, page: Page | None):
        for tentative in range(1, self.tentatives_sources + 1):
            try:
                return source.collecter(siren, page)
            except ConfigurationSourceInvalide:
                raise
            except ErreurAPI as erreur:
                if not erreur.temporaire or tentative == self.tentatives_sources:
                    raise
            except (ConnectionError, TimeoutError):
                if tentative == self.tentatives_sources:
                    raise
            except Exception:
                raise
            self.pause(self.delai_initial * (2 ** (tentative - 1)))

    def collecter(self, siren: str, page: Page | None = None) -> Societe:
        collectes = {}
        self.erreurs_sources = {}
        sources_officielles = [
            source for source in self.sources if source.nom != "Pappers"
        ]
        sources_pappers = [
            source for source in self.sources if source.nom == "Pappers"
        ]
        for source in sources_officielles:
            try:
                collectes[source.nom] = self._collecter_source(source, siren, page)
            except Exception as erreur:
                self.erreurs_sources[source.nom] = str(erreur)
        champs_disponibles = {
            champ
            for societe in collectes.values()
            for champ in self.CHAMPS_ESSENTIELS
            if str(getattr(societe, champ, "") or "").strip()
        }
        pappers_requis = (
            self.forcer_pappers
            or not set(self.CHAMPS_ESSENTIELS).issubset(champs_disponibles)
        )
        if pappers_requis:
            for source in sources_pappers:
                try:
                    collectes[source.nom] = self._collecter_source(source, siren, page)
                except Exception as erreur:
                    self.erreurs_sources[source.nom] = str(erreur)
        if not collectes:
            details = "; ".join(
                f"{source}: {erreur}"
                for source, erreur in self.erreurs_sources.items()
            )
            raise ErreurCollecteMultisource(
                f"Toutes les sources ont échoué pour {siren} : {details}"
            )

        resultat = Societe(siren=siren)
        self.provenance = {}
        self.contradictions = {}
        for champ, priorites in PRIORITES_CHAMPS.items():
            valeurs = {
                nom: str(getattr(societe, champ, "") or "").strip()
                for nom, societe in collectes.items()
                if str(getattr(societe, champ, "") or "").strip()
            }
            for nom in priorites:
                if nom in valeurs:
                    setattr(resultat, champ, valeurs[nom])
                    self.provenance[champ] = nom
                    break
            if _valeurs_contradictoires(champ, valeurs):
                self.contradictions[champ] = valeurs
        sources_utilisees = dict.fromkeys(self.provenance.values())
        resultat.source = " + ".join(sources_utilisees)
        resultat.provenance = dict(self.provenance)
        resultat.dates_provenance = {
            champ: resultat.date_collecte.isoformat(timespec="seconds")
            for champ in self.provenance
        }
        resultat.erreurs_sources = dict(self.erreurs_sources)
        resultat.contradictions = dict(self.contradictions)
        if "INPI" in collectes:
            resultat.documents_inpi = list(collectes["INPI"].documents_inpi)
        return resultat


SOURCES_DISPONIBLES = {
    "pappers": SourcePappers,
    "insee": SourceINSEE,
    "inpi": SourceINPI,
    "bodacc": SourceBODACC,
    "multisource": SourceMultisource,
}


def creer_source(nom: str):
    try:
        return SOURCES_DISPONIBLES[nom.casefold()]()
    except KeyError as erreur:
        choix = ", ".join(SOURCES_DISPONIBLES)
        raise ValueError(f"Source inconnue : {nom}. Choix : {choix}") from erreur
