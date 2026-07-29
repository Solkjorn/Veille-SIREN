import logging
from logging.handlers import RotatingFileHandler

from config import DOSSIER_LOGS


NOM_LOGGER = "VeilleSiren"
FICHIER_LOG = DOSSIER_LOGS / "veille.log"
TAILLE_MAX_LOG = 500 * 1024
NOMBRE_ARCHIVES = 1


def configurer_logger() -> logging.Logger:
    """
    Configure le journal du projet dans le dossier absolu ``logs``.

    La vérification des gestionnaires évite de dupliquer chaque ligne lorsque
    le module est importé plusieurs fois, notamment pendant les tests.
    """
    DOSSIER_LOGS.mkdir(parents=True, exist_ok=True)

    journal = logging.getLogger(NOM_LOGGER)
    journal.setLevel(logging.INFO)
    journal.propagate = False

    if journal.handlers:
        return journal

    gestionnaire = RotatingFileHandler(
        FICHIER_LOG,
        maxBytes=TAILLE_MAX_LOG,
        backupCount=NOMBRE_ARCHIVES,
        encoding="utf-8",
    )
    gestionnaire.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%d/%m/%Y %H:%M:%S",
        )
    )
    journal.addHandler(gestionnaire)

    return journal


logger = configurer_logger()
