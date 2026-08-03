import unittest
from unittest.mock import ANY, patch

from main import executer, executer_hebdomadaire
from modules.modele import SocieteSurveillee


class TestMain(unittest.TestCase):
    @patch("main.creer_sauvegarde", return_value="sauvegarde.zip")
    @patch("main.terminer_execution_veille")
    @patch("main.lire_resume_rapport_html", return_value={
        "societes": 4, "modifications": 1, "erreurs": 0,
    })
    @patch("main.demarrer_execution_veille", return_value=12)
    @patch("main.generer_synthese_hebdomadaire", return_value="synthese.html")
    @patch("main.envoyer_synthese")
    @patch("main.publier_synthese_hebdomadaire", return_value=None)
    @patch("main.executer", return_value="rapport.html")
    def test_execution_hebdomadaire_attend_la_fin_de_la_collecte(
        self, mock_executer, mock_publier_synthese, mock_envoyer, mock_synthese,
        mock_demarrer, mock_resume, mock_terminer, mock_sauvegarde,
    ):
        resultat = executer_hebdomadaire(source="inpi")

        mock_executer.assert_called_once_with(sans_interface=True, source="inpi")
        mock_synthese.assert_called_once_with()
        mock_publier_synthese.assert_called_once_with("synthese.html")
        mock_envoyer.assert_called_once_with("synthese.html")
        mock_demarrer.assert_called_once_with("hebdomadaire", "inpi")
        mock_terminer.assert_called_once_with(
            12, "succes", societes=4, modifications=1, erreurs=0,
            rapport="synthese.html",
        )
        mock_sauvegarde.assert_called_once_with(conserver=12)
        self.assertEqual(resultat, "synthese.html")

    @patch("main.publier_rapport_veille", return_value=None)
    @patch("main.generer_rapport", return_value="rapport.md")
    @patch("main.afficher_changements")
    @patch("main.detecter_changements", return_value=[])
    @patch("main.lire_derniere_collecte", return_value=None)
    @patch("main.enregistrer_societe")
    @patch("main.initialiser_base")
    @patch("main.logger")
    @patch("main.afficher_societe")
    @patch("main.CollecteurSocietes")
    @patch("main.lire_societes_surveillees")
    @patch("main.creer_dossiers")
    def test_executer_collecte_toutes_les_societes_actives(
        self, mock_creer_dossiers, mock_lire_societes, mock_collecteur_classe,
        mock_afficher, mock_logger, mock_initialiser, mock_enregistrer,
        mock_derniere, mock_detecter, mock_afficher_changements, mock_rapport,
        mock_publier,
    ):
        mock_lire_societes.return_value = [
            SocieteSurveillee("111111111"), SocieteSurveillee("333333333")
        ]
        mock_collecter = (
            mock_collecteur_classe.return_value.__enter__.return_value.collecter
        )
        mock_collecter.side_effect = ["société 1", "société 3"]

        executer()

        self.assertEqual(
            [appel.args[0] for appel in mock_collecter.call_args_list],
            ["111111111", "333333333"],
        )
        self.assertEqual(mock_enregistrer.call_count, 2)
        mock_lire_societes.assert_called_once_with(actives_uniquement=True)
        mock_rapport.assert_called_once()
        mock_publier.assert_called_once()
        mock_collecteur_classe.assert_called_once_with(
            sans_interface=False,
            tentatives=2,
            source=ANY,
        )

    @patch("main.publier_rapport_veille", return_value=None)
    @patch("main.generer_rapport", return_value="rapport.md")
    @patch("main.afficher_changements")
    @patch("main.detecter_changements", return_value=[])
    @patch("main.lire_derniere_collecte", return_value=None)
    @patch("main.enregistrer_societe")
    @patch("main.initialiser_base")
    @patch("main.logger")
    @patch("main.afficher_societe")
    @patch("main.CollecteurSocietes")
    @patch("main.lire_societes_surveillees")
    @patch("main.creer_dossiers")
    def test_executer_continue_apres_une_erreur_de_collecte(
        self, mock_creer_dossiers, mock_lire_societes, mock_collecteur_classe,
        mock_afficher, mock_logger, mock_initialiser, mock_enregistrer,
        mock_derniere, mock_detecter, mock_afficher_changements, mock_rapport,
        mock_publier,
    ):
        mock_lire_societes.return_value = [
            SocieteSurveillee("111111111"), SocieteSurveillee("333333333")
        ]
        mock_collecter = (
            mock_collecteur_classe.return_value.__enter__.return_value.collecter
        )
        mock_collecter.side_effect = [RuntimeError("Pappers indisponible"),
                                      "société 3"]

        executer()

        self.assertEqual(mock_collecter.call_count, 2)
        mock_enregistrer.assert_called_once_with("société 3")
        mock_rapport.assert_called_once()
        mock_publier.assert_called_once()
        self.assertEqual(
            mock_rapport.call_args.kwargs["erreurs"],
            [("111111111", "Pappers indisponible")],
        )


if __name__ == "__main__":
    unittest.main()
