import unittest

from modules.comparaison import detecter_changements
from modules.modele import Societe


class TestComparaison(unittest.TestCase):

    def test_premiere_collecte_ne_declenche_pas_d_alerte(self):
        nouvelle = Societe(siren="542051180", statut="Active")

        self.assertEqual(detecter_changements(None, nouvelle), [])

    def test_detecter_changements_retourne_les_champs_modifies(self):
        ancienne = Societe(
            siren="542051180",
            capital="100 000 €",
            statut="Active",
        )
        nouvelle = Societe(
            siren="542051180",
            capital="120 000 €",
            statut="Radiée",
        )

        changements = detecter_changements(ancienne, nouvelle)

        self.assertEqual(
            [changement.champ for changement in changements],
            ["capital", "statut"],
        )
        self.assertEqual(changements[0].ancienne_valeur, "100 000 €")
        self.assertEqual(changements[0].nouvelle_valeur, "120 000 €")

    def test_deux_etats_identiques_ne_declenchent_pas_d_alerte(self):
        ancienne = Societe(siren="542051180", statut="Active")
        nouvelle = Societe(siren="542051180", statut="Active")

        self.assertEqual(detecter_changements(ancienne, nouvelle), [])


if __name__ == "__main__":
    unittest.main()
