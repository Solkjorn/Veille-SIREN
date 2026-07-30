import tempfile
import unittest
from pathlib import Path

from modules.societes_surveillees import (
    ajouter_societe_surveillee,
    lire_societe_surveillee,
    lire_societes_surveillees,
    modifier_societe_surveillee,
    supprimer_societe_surveillee,
)


class TestSocietesSurveillees(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name) / "test.sqlite"

    def tearDown(self):
        self.temp.cleanup()

    def test_cycle_crud_avec_archivage(self):
        ajoutee = ajouter_societe_surveillee(
            "542051180", commentaire="Groupe énergie", chemin=self.base
        )
        self.assertTrue(ajoutee.actif)
        modifiee = modifier_societe_surveillee(
            "542051180", actif=False, commentaire="Suspendue", chemin=self.base
        )
        self.assertFalse(modifiee.actif)
        archivee = supprimer_societe_surveillee("542051180", self.base)
        self.assertIsNotNone(archivee.date_archivage)
        self.assertEqual(lire_societes_surveillees(chemin=self.base), [])
        self.assertIsNotNone(lire_societe_surveillee("542051180", self.base))

    def test_refuse_siren_invalide_et_doublon(self):
        with self.assertRaises(ValueError):
            ajouter_societe_surveillee("123", chemin=self.base)
        ajouter_societe_surveillee("542051180", chemin=self.base)
        with self.assertRaises(ValueError):
            ajouter_societe_surveillee("542051180", chemin=self.base)

    def test_filtre_les_societes_actives(self):
        ajouter_societe_surveillee("542051180", chemin=self.base)
        ajouter_societe_surveillee("552032534", actif=False, chemin=self.base)
        societes = lire_societes_surveillees(
            actives_uniquement=True, chemin=self.base
        )
        self.assertEqual([s.siren for s in societes], ["542051180"])


if __name__ == "__main__":
    unittest.main()
