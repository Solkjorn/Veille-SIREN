import unittest
from unittest.mock import patch

from main import executer
from modules.modele import SocieteSurveillee


class TestMain(unittest.TestCase):
    @patch("main.generer_rapport", return_value="rapport.md")
    @patch("main.afficher_changements")
    @patch("main.detecter_changements", return_value=[])
    @patch("main.lire_derniere_collecte", return_value=None)
    @patch("main.enregistrer_societe")
    @patch("main.initialiser_base")
    @patch("main.logger")
    @patch("main.afficher_societe")
    @patch("main.collecter_societe")
    @patch("main.lire_societes_surveillees")
    @patch("main.creer_dossiers")
    def test_executer_collecte_toutes_les_societes_actives(
        self, mock_creer_dossiers, mock_lire_societes, mock_collecter,
        mock_afficher, mock_logger, mock_initialiser, mock_enregistrer,
        mock_derniere, mock_detecter, mock_afficher_changements, mock_rapport,
    ):
        mock_lire_societes.return_value = [
            SocieteSurveillee("111111111"), SocieteSurveillee("333333333")
        ]
        mock_collecter.side_effect = ["société 1", "société 3"]

        executer()

        self.assertEqual(
            [appel.args[0] for appel in mock_collecter.call_args_list],
            ["111111111", "333333333"],
        )
        self.assertEqual(mock_enregistrer.call_count, 2)
        mock_lire_societes.assert_called_once_with(actives_uniquement=True)
        mock_rapport.assert_called_once()

    @patch("main.generer_rapport", return_value="rapport.md")
    @patch("main.afficher_changements")
    @patch("main.detecter_changements", return_value=[])
    @patch("main.lire_derniere_collecte", return_value=None)
    @patch("main.enregistrer_societe")
    @patch("main.initialiser_base")
    @patch("main.logger")
    @patch("main.afficher_societe")
    @patch("main.collecter_societe")
    @patch("main.lire_societes_surveillees")
    @patch("main.creer_dossiers")
    def test_executer_continue_apres_une_erreur_de_collecte(
        self, mock_creer_dossiers, mock_lire_societes, mock_collecter,
        mock_afficher, mock_logger, mock_initialiser, mock_enregistrer,
        mock_derniere, mock_detecter, mock_afficher_changements, mock_rapport,
    ):
        mock_lire_societes.return_value = [
            SocieteSurveillee("111111111"), SocieteSurveillee("333333333")
        ]
        mock_collecter.side_effect = [RuntimeError("Pappers indisponible"),
                                      "société 3"]

        executer()

        self.assertEqual(mock_collecter.call_count, 2)
        mock_enregistrer.assert_called_once_with("société 3")
        mock_rapport.assert_called_once()


if __name__ == "__main__":
    unittest.main()
