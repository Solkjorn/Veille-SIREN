import unittest
from unittest.mock import MagicMock, patch

from modules.sources import (
    ConfigurationSourceInvalide,
    SourceBODACC,
    SourceINPI,
    SourceINSEE,
    SourcePappers,
    creer_source,
)


class TestSources(unittest.TestCase):
    @patch("modules.sources.lire_pappers_avec_page", return_value="société")
    def test_source_pappers_respecte_le_contrat(self, mock_lire):
        page = MagicMock()

        resultat = SourcePappers().collecter("123456789", page)

        self.assertEqual(resultat, "société")
        self.assertEqual(SourcePappers.nom, "Pappers")
        mock_lire.assert_called_once_with("123456789", page)

    @patch("modules.sources.requete_json")
    def test_source_insee_convertit_une_unite_legale(self, mock_requete):
        mock_requete.return_value = {
            "uniteLegale": {
                "periodesUniteLegale": [{
                    "denominationUniteLegale": "SOCIÉTÉ INSEE",
                    "categorieJuridiqueUniteLegale": "5710",
                    "etatAdministratifUniteLegale": "A",
                }]
            }
        }

        societe = SourceINSEE(cle_api="cle-test").collecter("123456789")

        self.assertEqual(societe.raison_sociale, "SOCIÉTÉ INSEE")
        self.assertEqual(societe.forme_juridique, "5710")
        self.assertEqual(societe.statut, "Active")
        self.assertEqual(societe.source, "INSEE")
        self.assertEqual(
            mock_requete.call_args.args[1],
            {"X-INSEE-Api-Key-Integration": "cle-test"},
        )

    @patch("modules.sources.lire_cle_insee", return_value="")
    def test_source_insee_refuse_une_cle_absente(self, mock_coffre):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ConfigurationSourceInvalide):
                SourceINSEE().collecter("123456789")

        mock_coffre.assert_called_once_with()

    @patch("modules.sources.lire_cle_insee", return_value="cle-coffre")
    def test_source_insee_lit_la_cle_du_coffre_windows(self, mock_coffre):
        with patch.dict("os.environ", {}, clear=True):
            source = SourceINSEE()

        self.assertEqual(source.cle_api, "cle-coffre")
        mock_coffre.assert_called_once_with()

    @patch("modules.sources.lire_identifiants_inpi", return_value=("", ""))
    @patch("modules.sources.requete_json")
    def test_source_inpi_s_authentifie_et_convertit_la_societe(
        self, mock_requete, mock_coffre
    ):
        mock_requete.side_effect = [
            {"token": "jeton-test"},
            {"formality": {"content": {
                "personneMorale": {"identite": {"entreprise": {
                    "denomination": "SOCIÉTÉ INPI",
                    "formeJuridique": "SAS",
                }}}
            }}},
        ]

        societe = SourceINPI("compte", "secret").collecter("123456789")

        self.assertEqual(societe.raison_sociale, "SOCIÉTÉ INPI")
        self.assertEqual(societe.forme_juridique, "SAS")
        self.assertEqual(societe.source, "INPI")
        self.assertEqual(mock_requete.call_count, 2)
        mock_coffre.assert_called_once_with()
        self.assertEqual(
            mock_requete.call_args.args[1],
            {"Authorization": "Bearer jeton-test"},
        )

    @patch("modules.sources.lire_identifiants_inpi", return_value=("", ""))
    def test_source_inpi_refuse_une_configuration_absente(self, mock_coffre):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ConfigurationSourceInvalide):
                SourceINPI().collecter("123456789")
        mock_coffre.assert_called_once_with()

    @patch(
        "modules.sources.lire_identifiants_inpi",
        return_value=("compte-coffre", "secret-coffre"),
    )
    def test_source_inpi_lit_les_identifiants_du_coffre(self, mock_coffre):
        with patch.dict("os.environ", {}, clear=True):
            source = SourceINPI()

        self.assertEqual(source.identifiant, "compte-coffre")
        self.assertEqual(source.mot_de_passe, "secret-coffre")
        mock_coffre.assert_called_once_with()

    @patch("modules.sources.requete_json")
    def test_source_bodacc_convertit_la_derniere_annonce(self, mock_requete):
        mock_requete.return_value = {"results": [{
            "commercant": "SOCIÉTÉ BODACC",
            "dateparution": "2026-07-30",
            "typeavis": "Modification",
            "modificationsgenerales": "Capital porté à 20 000 euros",
        }]}

        societe = SourceBODACC().collecter("123456789")

        self.assertEqual(societe.raison_sociale, "SOCIÉTÉ BODACC")
        self.assertEqual(societe.derniere_publication_bodacc, "2026-07-30")
        self.assertIn("Modification", societe.dernier_changement)
        self.assertEqual(societe.source, "BODACC")

    def test_fabrique_connait_les_quatre_sources(self):
        self.assertIsInstance(creer_source("pappers"), SourcePappers)
        self.assertIsInstance(creer_source("insee"), SourceINSEE)
        self.assertIsInstance(creer_source("inpi"), SourceINPI)
        self.assertIsInstance(creer_source("bodacc"), SourceBODACC)


if __name__ == "__main__":
    unittest.main()
