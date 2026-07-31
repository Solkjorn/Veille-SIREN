import unittest
from unittest.mock import MagicMock, patch

from modules.collecteur import CollecteurSocietes


class TestCollecteurSocietes(unittest.TestCase):
    @patch("modules.collecteur.enregistrer_etat_tache")
    @patch("modules.collecteur.Navigateur")
    def test_reutilise_le_navigateur_et_ferme_chaque_page(
        self, mock_navigateur_classe, mock_etat
    ):
        source = MagicMock()
        navigateur = mock_navigateur_classe.return_value
        page_1 = MagicMock()
        page_2 = MagicMock()
        navigateur.nouvelle_page.side_effect = [page_1, page_2]
        source.collecter.side_effect = ["société 1", "société 2"]

        with CollecteurSocietes(
            sans_interface=True, source=source
        ) as collecteur:
            self.assertEqual(collecteur.collecter("111111111"), "société 1")
            self.assertEqual(collecteur.collecter("222222222"), "société 2")

        mock_navigateur_classe.assert_called_once_with(sans_interface=True)
        navigateur.ouvrir.assert_called_once_with()
        navigateur.fermer.assert_called_once_with()
        page_1.close.assert_called_once_with()
        page_2.close.assert_called_once_with()
        self.assertEqual(mock_etat.call_count, 4)

    @patch("modules.collecteur.enregistrer_etat_tache")
    @patch("modules.collecteur.Navigateur")
    def test_ferme_la_page_apres_une_erreur(
        self, mock_navigateur_classe, mock_etat
    ):
        source = MagicMock()
        page = mock_navigateur_classe.return_value.nouvelle_page.return_value
        source.collecter.side_effect = RuntimeError("source indisponible")

        with CollecteurSocietes(source=source) as collecteur:
            with self.assertRaisesRegex(RuntimeError, "source indisponible"):
                collecteur.collecter("111111111")

        page.close.assert_called_once_with()
        self.assertEqual(mock_etat.call_args_list[-1].args[1], "echec")

    @patch("modules.collecteur.enregistrer_etat_tache")
    @patch("modules.collecteur.Navigateur")
    def test_reessaie_apres_une_erreur_temporaire(
        self, mock_navigateur_classe, mock_etat
    ):
        source = MagicMock()
        navigateur = mock_navigateur_classe.return_value
        navigateur.nouvelle_page.side_effect = [MagicMock(), MagicMock()]
        source.collecter.side_effect = [TimeoutError("délai"), "société"]

        with CollecteurSocietes(tentatives=2, source=source) as collecteur:
            resultat = collecteur.collecter("111111111")

        self.assertEqual(resultat, "société")
        self.assertEqual(source.collecter.call_count, 2)
        statuts = [appel.args[1] for appel in mock_etat.call_args_list]
        self.assertEqual(
            statuts,
            ["en_cours", "nouvelle_tentative", "en_cours", "reussie"],
        )


if __name__ == "__main__":
    unittest.main()
