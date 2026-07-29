import unittest
from unittest.mock import patch

from main import est_active, executer


class TestMain(unittest.TestCase):

    def test_est_active_reconnait_les_valeurs_positives(self):
        for valeur in ("Oui", "oui", "O", "1", "true", "VRAI"):
            with self.subTest(valeur=valeur):
                self.assertTrue(est_active(valeur))

    def test_est_active_refuse_les_autres_valeurs(self):
        for valeur in ("Non", "", None, "0", "faux"):
            with self.subTest(valeur=valeur):
                self.assertFalse(est_active(valeur))

    @patch("main.generer_rapport", return_value="rapport.md")
    @patch("main.afficher_changements")
    @patch("main.detecter_changements", return_value=[])
    @patch("main.lire_derniere_collecte", return_value=None)
    @patch("main.enregistrer_societe")
    @patch("main.initialiser_base")
    @patch("main.logger")
    @patch("main.afficher_societe")
    @patch("main.collecter_societe")
    @patch("main.siren_valide", return_value=True)
    @patch("main.lire_sirens")
    @patch("main.creer_dossiers")
    def test_executer_collecte_toutes_les_societes_actives(
        self,
        mock_creer_dossiers,
        mock_lire_sirens,
        mock_siren_valide,
        mock_collecter_societe,
        mock_afficher_societe,
        mock_logger,
        mock_initialiser_base,
        mock_enregistrer_societe,
        mock_lire_derniere_collecte,
        mock_detecter_changements,
        mock_afficher_changements,
        mock_generer_rapport,
    ):
        mock_lire_sirens.return_value = [
            {"siren": "111111111", "actif": "Oui", "commentaire": ""},
            {"siren": "222222222", "actif": "Non", "commentaire": ""},
            {"siren": "333333333", "actif": "Oui", "commentaire": ""},
        ]
        mock_collecter_societe.side_effect = ["société 1", "société 3"]

        executer()

        self.assertEqual(
            [appel.args[0] for appel in mock_collecter_societe.call_args_list],
            ["111111111", "333333333"],
        )
        self.assertEqual(mock_afficher_societe.call_count, 2)
        self.assertEqual(mock_enregistrer_societe.call_count, 2)
        self.assertEqual(mock_afficher_changements.call_count, 2)
        mock_generer_rapport.assert_called_once()

    @patch("main.generer_rapport", return_value="rapport.md")
    @patch("main.afficher_changements")
    @patch("main.detecter_changements", return_value=[])
    @patch("main.lire_derniere_collecte", return_value=None)
    @patch("main.enregistrer_societe")
    @patch("main.initialiser_base")
    @patch("main.logger")
    @patch("main.afficher_societe")
    @patch("main.collecter_societe")
    @patch("main.siren_valide", return_value=True)
    @patch("main.lire_sirens")
    @patch("main.creer_dossiers")
    def test_executer_continue_apres_une_erreur_de_collecte(
        self,
        mock_creer_dossiers,
        mock_lire_sirens,
        mock_siren_valide,
        mock_collecter_societe,
        mock_afficher_societe,
        mock_logger,
        mock_initialiser_base,
        mock_enregistrer_societe,
        mock_lire_derniere_collecte,
        mock_detecter_changements,
        mock_afficher_changements,
        mock_generer_rapport,
    ):
        mock_lire_sirens.return_value = [
            {"siren": "111111111", "actif": "Oui", "commentaire": ""},
            {"siren": "333333333", "actif": "Oui", "commentaire": ""},
        ]
        mock_collecter_societe.side_effect = [
            RuntimeError("Pappers indisponible"),
            "société 3",
        ]

        executer()

        self.assertEqual(mock_collecter_societe.call_count, 2)
        mock_afficher_societe.assert_called_once_with("société 3")
        mock_enregistrer_societe.assert_called_once_with("société 3")
        mock_afficher_changements.assert_called_once_with([])
        mock_generer_rapport.assert_called_once()


if __name__ == "__main__":
    unittest.main()
