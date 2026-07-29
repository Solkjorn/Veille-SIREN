from logging.handlers import RotatingFileHandler
import unittest

from config import DOSSIER_LOGS
from modules.logger import (
    FICHIER_LOG,
    NOMBRE_ARCHIVES,
    NOM_LOGGER,
    TAILLE_MAX_LOG,
    configurer_logger,
)


class TestLogger(unittest.TestCase):

    def test_fichier_log_est_dans_le_dossier_du_projet(self):
        self.assertEqual(FICHIER_LOG, DOSSIER_LOGS / "veille.log")
        self.assertTrue(FICHIER_LOG.is_absolute())

    def test_configurer_logger_ne_duplique_pas_les_gestionnaires(self):
        journal = configurer_logger()
        nombre_gestionnaires = len(journal.handlers)

        meme_journal = configurer_logger()

        self.assertIs(journal, meme_journal)
        self.assertEqual(journal.name, NOM_LOGGER)
        self.assertEqual(len(meme_journal.handlers), nombre_gestionnaires)
        self.assertTrue(
            any(
                isinstance(gestionnaire, RotatingFileHandler)
                for gestionnaire in journal.handlers
            )
        )

    def test_journal_est_limite_a_500_ko_avec_une_archive(self):
        journal = configurer_logger()
        gestionnaire = next(
            gestionnaire
            for gestionnaire in journal.handlers
            if isinstance(gestionnaire, RotatingFileHandler)
        )

        self.assertEqual(TAILLE_MAX_LOG, 500 * 1024)
        self.assertEqual(NOMBRE_ARCHIVES, 1)
        self.assertEqual(gestionnaire.maxBytes, TAILLE_MAX_LOG)
        self.assertEqual(gestionnaire.backupCount, NOMBRE_ARCHIVES)


if __name__ == "__main__":
    unittest.main()
