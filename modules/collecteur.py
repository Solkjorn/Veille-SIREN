from threading import Lock

from playwright.sync_api import TimeoutError as ErreurDelaiPlaywright

from modules.base_donnees import enregistrer_etat_tache
from modules.modele import Societe
from modules.navigateur import Navigateur
from modules.pappers import lire_pappers
from modules.sources import SourcePappers


class CollecteDejaEnCours(RuntimeError):
    pass


_verrous_siren: dict[str, Lock] = {}
_verrou_registre = Lock()


def _verrou_pour(siren: str) -> Lock:
    with _verrou_registre:
        return _verrous_siren.setdefault(siren, Lock())


class CollecteurSocietes:
    """Collecteur réutilisant une même session de navigateur."""

    def __init__(
        self,
        sans_interface: bool = False,
        tentatives: int = 2,
        source=None,
    ):
        if tentatives < 1:
            raise ValueError("Le nombre de tentatives doit être positif.")
        self.navigateur = Navigateur(sans_interface=sans_interface)
        self.tentatives = tentatives
        self.source = source or SourcePappers()

    def __enter__(self):
        if self.source.necessite_navigateur:
            self.navigateur.ouvrir()
        return self

    def __exit__(self, type_erreur, erreur, trace):
        if self.source.necessite_navigateur:
            self.navigateur.fermer()

    def collecter(self, siren: str) -> Societe:
        siren = str(siren).strip()
        verrou = _verrou_pour(siren)
        if not verrou.acquire(blocking=False):
            raise CollecteDejaEnCours(
                f"Une collecte est déjà en cours pour le SIREN {siren}."
            )
        try:
            for tentative in range(1, self.tentatives + 1):
                enregistrer_etat_tache(siren, "en_cours", tentative)
                page = (
                    self.navigateur.nouvelle_page()
                    if self.source.necessite_navigateur
                    else None
                )
                try:
                    societe = self.source.collecter(siren, page)
                except (TimeoutError, ConnectionError, ErreurDelaiPlaywright) as erreur:
                    if tentative == self.tentatives:
                        enregistrer_etat_tache(
                            siren, "echec", tentative, str(erreur)
                        )
                        raise
                    enregistrer_etat_tache(
                        siren, "nouvelle_tentative", tentative, str(erreur)
                    )
                except Exception as erreur:
                    enregistrer_etat_tache(
                        siren, "echec", tentative, str(erreur)
                    )
                    raise
                else:
                    enregistrer_etat_tache(siren, "reussie", tentative)
                    return societe
                finally:
                    if page is not None:
                        page.close()
        finally:
            verrou.release()


def collecter_societe(siren: str) -> Societe:
    """
    Collecte les informations disponibles pour une société.

    Pour le moment, la collecte utilise uniquement Pappers.
    D'autres sources seront ajoutées ensuite.
    """

    societe = lire_pappers(siren)

    return societe
