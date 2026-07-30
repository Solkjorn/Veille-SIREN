import tempfile
import unittest
from pathlib import Path

from modules.societes_surveillees import (
    activer_societe_surveillee,
    ajouter_societe_surveillee,
    desactiver_societe_surveillee,
    lire_societe_surveillee,
    lire_societes_surveillees,
    modifier_societe_surveillee,
    restaurer_societe_surveillee,
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

    def test_activation_et_desactivation_explicites(self):
        ajouter_societe_surveillee("542051180", chemin=self.base)

        desactivee = desactiver_societe_surveillee(
            "542051180", chemin=self.base
        )
        self.assertFalse(desactivee.actif)
        self.assertIsNone(desactivee.date_archivage)

        activee = activer_societe_surveillee("542051180", chemin=self.base)
        self.assertTrue(activee.actif)
        self.assertIsNone(activee.date_archivage)

    def test_restaure_une_societe_archivee(self):
        ajouter_societe_surveillee("542051180", chemin=self.base)
        supprimer_societe_surveillee("542051180", chemin=self.base)

        restauree = restaurer_societe_surveillee(
            "542051180", chemin=self.base
        )

        self.assertTrue(restauree.actif)
        self.assertIsNone(restauree.date_archivage)
        self.assertEqual(
            [societe.siren for societe in lire_societes_surveillees(
                actives_uniquement=True, chemin=self.base
            )],
            ["542051180"],
        )

    def test_refuse_les_transitions_incoherentes(self):
        ajouter_societe_surveillee("542051180", chemin=self.base)
        with self.assertRaises(KeyError):
            restaurer_societe_surveillee("542051180", chemin=self.base)

        supprimer_societe_surveillee("542051180", chemin=self.base)
        with self.assertRaises(KeyError):
            activer_societe_surveillee("542051180", chemin=self.base)


if __name__ == "__main__":
    unittest.main()
