import json
import unittest
from unittest.mock import MagicMock, patch

from modules.modele import Societe
from modules.client_http import ErreurAPI
from modules.sources import (
    ConfigurationSourceInvalide,
    SourceAnnuaireEntreprises,
    SourceBODACC,
    SourceINPI,
    SourceINSEE,
    SourceMultisource,
    SourcePappers,
    creer_source,
)


class TestSources(unittest.TestCase):
    @patch("modules.sources.requete_json")
    def test_source_annuaire_convertit_une_fiche_officielle(self, mock_requete):
        mock_requete.return_value = {"results": [{
            "siren": "123456789",
            "nom_raison_sociale": "SOCIÉTÉ ANNUAIRE",
            "nature_juridique": "5499",
            "etat_administratif": "A",
            "siege": {"adresse": "1 RUE DE PARIS 75001 PARIS"},
            "dirigeants": [{
                "prenoms": "Jane", "nom": "Doe", "qualite": "Gérante",
            }],
        }]}

        societe = SourceAnnuaireEntreprises().collecter("123456789")

        self.assertEqual(societe.raison_sociale, "SOCIÉTÉ ANNUAIRE")
        self.assertEqual(societe.forme_juridique, "5499")
        self.assertEqual(societe.statut, "Active")
        self.assertEqual(societe.adresse, "1 RUE DE PARIS 75001 PARIS")
        self.assertEqual(societe.dirigeant, "Jane Doe (Gérante)")
        self.assertEqual(societe.source, "Annuaire des entreprises")
        self.assertIn("q=123456789", mock_requete.call_args.args[0])
        self.assertIn("User-Agent", mock_requete.call_args.args[1])

    @patch("modules.sources.requete_json", return_value={"results": []})
    def test_source_annuaire_tolere_un_siren_absent(self, mock_requete):
        societe = SourceAnnuaireEntreprises().collecter("123456789")

        self.assertEqual(societe.siren, "123456789")
        self.assertEqual(societe.raison_sociale, "")

    @patch("modules.sources.requete_json")
    def test_source_annuaire_conserve_le_nom_complet_d_un_independant(self, mock_requete):
        mock_requete.return_value = {"results": [{
            "siren": "123456789", "nom_complet": "CLAUDE ZERMATTI",
            "nom_raison_sociale": "CLAUDE", "nature_juridique": "1000",
        }]}

        societe = SourceAnnuaireEntreprises().collecter("123456789")

        self.assertEqual(societe.raison_sociale, "CLAUDE ZERMATTI")

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

    @patch("modules.sources.requete_json")
    def test_source_insee_conserve_prenom_et_nom_d_un_independant(self, mock_requete):
        mock_requete.return_value = {"uniteLegale": {
            "prenomUsuelUniteLegale": "CLAUDE",
            "periodesUniteLegale": [{
                "nomUniteLegale": "ZERMATTI",
                "categorieJuridiqueUniteLegale": "1000",
                "etatAdministratifUniteLegale": "A",
            }],
        }}

        societe = SourceINSEE(cle_api="cle-test").collecter("123456789")

        self.assertEqual(societe.raison_sociale, "CLAUDE ZERMATTI")

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
            {"actes": [{
                "id": "acte-1", "dateDepot": "2026-07-30",
                "libelle": "Statuts mis à jour", "confidentiality": "Public",
            }], "bilans": [], "bilansSaisis": []},
        ]

        societe = SourceINPI("compte", "secret").collecter("123456789")

        self.assertEqual(societe.raison_sociale, "SOCIÉTÉ INPI")
        self.assertEqual(societe.forme_juridique, "SAS")
        self.assertEqual(societe.source, "INPI")
        self.assertEqual(mock_requete.call_count, 3)
        self.assertEqual(societe.documents_inpi[0]["identifiant"], "acte-1")
        mock_coffre.assert_called_once_with()
        self.assertEqual(
            mock_requete.call_args.args[1],
            {"Authorization": "Bearer jeton-test"},
        )

    @patch("modules.sources.requete_binaire", return_value=(b"%PDF", "application/pdf"))
    @patch("modules.sources.lire_identifiants_inpi", return_value=("", ""))
    def test_source_inpi_telecharge_un_document_a_la_demande(
        self, mock_coffre, mock_binaire
    ):
        source = SourceINPI("compte", "secret")
        source._jeton = "jeton-test"
        contenu, type_mime = source.telecharger_document("acte", "abc/123")
        self.assertEqual(contenu, b"%PDF")
        self.assertEqual(type_mime, "application/pdf")
        self.assertIn("/actes/abc%2F123/download", mock_binaire.call_args.args[0])

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

    @patch("modules.sources.requete_json")
    def test_source_bodacc_detaille_un_depot_json(self, mock_requete):
        mock_requete.return_value = {"results": [{
            "commercant": "SOCIÉTÉ BODACC",
            "dateparution": "2026-08-01",
            "typeavis": "annonce",
            "familleavis_lib": "Dépôts des comptes",
            "depot": json.dumps({
                "typeDepot": "Comptes annuels",
                "dateCloture": "2025-12-31",
            }),
        }]}

        societe = SourceBODACC().collecter("123456789")

        self.assertIn("Dépôts des comptes", societe.dernier_changement)
        self.assertIn("Comptes annuels", societe.dernier_changement)

    def test_fabrique_connait_toutes_les_sources(self):
        self.assertIsInstance(creer_source("annuaire"), SourceAnnuaireEntreprises)
        self.assertIsInstance(creer_source("pappers"), SourcePappers)
        self.assertIsInstance(creer_source("insee"), SourceINSEE)
        self.assertIsInstance(creer_source("inpi"), SourceINPI)
        self.assertIsInstance(creer_source("bodacc"), SourceBODACC)
        self.assertIsInstance(creer_source("multisource"), SourceMultisource)

    def test_multisource_fusionne_selon_les_priorites(self):
        insee = MagicMock(nom="INSEE", necessite_navigateur=False)
        insee.collecter.return_value = Societe(
            "123456789", raison_sociale="Nom officiel", statut="Active",
            forme_juridique="5710", source="INSEE",
        )
        inpi = MagicMock(nom="INPI", necessite_navigateur=False)
        inpi.collecter.return_value = Societe(
            "123456789", raison_sociale="Nom différent", forme_juridique="SAS",
            dirigeant="Direction officielle", source="INPI",
        )
        bodacc = MagicMock(nom="BODACC", necessite_navigateur=False)
        bodacc.collecter.return_value = Societe(
            "123456789", derniere_publication_bodacc="2026-08-01",
            dernier_changement="Modification", source="BODACC",
        )
        source = SourceMultisource([insee, inpi, bodacc])

        societe = source.collecter("123456789")

        self.assertEqual(societe.raison_sociale, "Nom officiel")
        self.assertEqual(societe.forme_juridique, "SAS")
        self.assertEqual(societe.dernier_changement, "Modification")
        self.assertEqual(source.provenance["statut"], "INSEE")
        self.assertIn("raison_sociale", source.contradictions)

    def test_multisource_ne_remplace_pas_un_libelle_par_un_code_juridique(self):
        annuaire = MagicMock(nom="Annuaire des entreprises", necessite_navigateur=False)
        annuaire.collecter.return_value = Societe(
            "123456789", forme_juridique="6540", source="Annuaire des entreprises"
        )
        insee = MagicMock(nom="INSEE", necessite_navigateur=False)
        insee.collecter.return_value = Societe(
            "123456789", forme_juridique="6540", source="INSEE"
        )

        societe = SourceMultisource([annuaire, insee]).collecter("123456789")

        self.assertEqual(societe.forme_juridique, "")
        self.assertNotIn("forme_juridique", societe.provenance)

    def test_multisource_traduit_une_categorie_juridique_connue(self):
        annuaire = MagicMock(nom="Annuaire des entreprises", necessite_navigateur=False)
        annuaire.collecter.return_value = Societe(
            "123456789", forme_juridique="8420", source="Annuaire des entreprises"
        )

        societe = SourceMultisource([annuaire]).collecter("123456789")

        self.assertEqual(societe.forme_juridique, "Syndicat patronal")
        self.assertEqual(societe.provenance["forme_juridique"], "Nomenclature INSEE")

    def test_multisource_continue_si_une_source_echoue(self):
        source_erreur = MagicMock(nom="INSEE", necessite_navigateur=False)
        source_erreur.collecter.side_effect = ConnectionError("indisponible")
        source_valide = MagicMock(nom="BODACC", necessite_navigateur=False)
        source_valide.collecter.return_value = Societe(
            "123456789", dernier_changement="Création", source="BODACC"
        )
        source = SourceMultisource([source_erreur, source_valide])

        societe = source.collecter("123456789")

        self.assertEqual(societe.dernier_changement, "Création")
        self.assertIn("INSEE", source.erreurs_sources)

    def test_multisource_ne_signale_pas_un_resume_bodacc_comme_conflit(self):
        bodacc = MagicMock(nom="BODACC", necessite_navigateur=False)
        bodacc.collecter.return_value = Societe(
            "123456789",
            dernier_changement="Dépôts des comptes — Comptes annuels — 2025-12-31",
            source="BODACC",
        )
        pappers = MagicMock(nom="Pappers", necessite_navigateur=True)
        pappers.collecter.return_value = Societe(
            "123456789", dernier_changement="DÉPÔT DES COMPTES", source="Pappers"
        )
        source = SourceMultisource([bodacc, pappers])

        source.collecter("123456789", MagicMock())

        self.assertNotIn("dernier_changement", source.contradictions)

    @patch("modules.sources.lire_identifiants_inpi", return_value=("", ""))
    @patch("modules.sources.lire_cle_insee", return_value="")
    def test_multisource_par_defaut_exclut_pappers_et_le_navigateur(
        self, mock_insee, mock_inpi
    ):
        source = SourceMultisource()

        self.assertNotIn("Pappers", [element.nom for element in source.sources])
        self.assertIn(
            "Annuaire des entreprises", [element.nom for element in source.sources]
        )
        self.assertFalse(source.necessite_navigateur)

    def test_multisource_applique_des_delais_progressifs(self):
        source_api = MagicMock(nom="INSEE", necessite_navigateur=False)
        source_api.collecter.side_effect = [
            ErreurAPI("temporaire"),
            ErreurAPI("temporaire"),
            Societe("123456789", raison_sociale="Société", source="INSEE"),
        ]
        pauses = []
        source = SourceMultisource(
            [source_api], tentatives_sources=3,
            delai_initial=1, pause=pauses.append,
        )

        resultat = source.collecter("123456789")

        self.assertEqual(resultat.raison_sociale, "Société")
        self.assertEqual(pauses, [1, 2])

    def test_multisource_ne_reessaie_pas_une_erreur_api_permanente(self):
        source_api = MagicMock(nom="INSEE", necessite_navigateur=False)
        source_api.collecter.side_effect = ErreurAPI(
            "non autorisé", temporaire=False
        )
        source = SourceMultisource(
            [source_api], pause=MagicMock()
        )

        with self.assertRaises(Exception):
            source.collecter("123456789")

        source_api.collecter.assert_called_once()


if __name__ == "__main__":
    unittest.main()
