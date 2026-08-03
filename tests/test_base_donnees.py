import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime
from pathlib import Path

from modules.base_donnees import (
    changer_statut_alerte,
    configurer_preferences_alertes,
    configurer_destinataire_portefeuille,
    configurer_reglages_conservation,
    creer_portefeuille,
    enregistrer_audit,
    configurer_cible_notion,
    demarrer_execution_veille,
    enregistrer_etat_tache,
    enregistrer_alertes,
    enregistrer_publication_notion,
    enregistrer_societe,
    initialiser_base,
    lire_collectes_societe,
    lire_collectes_recentes,
    lire_collectes_entre,
    lire_collecte_avant,
    lire_derniere_collecte,
    lire_document_inpi,
    lire_documents_inpi,
    lire_erreurs_taches_entre,
    lire_executions_veille,
    lire_cible_notion,
    lire_alertes,
    lire_preferences_alertes,
    lire_portefeuilles,
    lire_reglages_conservation,
    lire_audit,
    publication_notion_existe,
    terminer_execution_veille,
)
from modules.comparaison import Changement
from modules.modele import Societe


class TestBaseDonnees(unittest.TestCase):

    def test_reglages_de_conservation_valides_et_persistants(self):
        self.assertEqual(
            lire_reglages_conservation(self.chemin_base),
            {"rapports_jours": 365, "sauvegardes_nombre": 12},
        )
        configurer_reglages_conservation(730, 24, self.chemin_base)
        self.assertEqual(
            lire_reglages_conservation(self.chemin_base),
            {"rapports_jours": 730, "sauvegardes_nombre": 24},
        )
        with self.assertRaises(ValueError):
            configurer_reglages_conservation(0, 24, self.chemin_base)


    def test_portefeuille_destinataire_et_journal_audit(self):
        identifiant = creer_portefeuille(
            "Clients", destinataire="initial@test.fr", chemin=self.chemin_base
        )
        configurer_destinataire_portefeuille(
            identifiant, "equipe@test.fr", self.chemin_base
        )
        enregistrer_audit(
            "configuration_destinataire", str(identifiant), chemin=self.chemin_base
        )

        self.assertEqual(
            lire_portefeuilles(self.chemin_base)[0]["destinataire"],
            "equipe@test.fr",
        )
        self.assertEqual(lire_audit(10, self.chemin_base)[0]["action"],
                         "configuration_destinataire")
        with self.assertRaisesRegex(ValueError, "invalide"):
            configurer_destinataire_portefeuille(
                identifiant, "adresse-invalide", self.chemin_base
            )

    def setUp(self):
        self.dossier_temporaire = tempfile.TemporaryDirectory()
        self.chemin_base = (
            Path(self.dossier_temporaire.name) / "veille_test.sqlite"
        )

    def tearDown(self):
        self.dossier_temporaire.cleanup()

    def test_enregistre_et_dedoublonne_les_documents_inpi(self):
        societe = Societe(
            "542051180",
            documents_inpi=[{
                "identifiant": "acte-1", "type_document": "acte",
                "date_depot": "2026-08-02", "libelle": "Statuts mis à jour",
                "nom_document": "statuts", "confidentialite": "Public",
            }],
        )
        enregistrer_societe(societe, self.chemin_base)
        enregistrer_societe(societe, self.chemin_base)
        documents = lire_documents_inpi("542051180", self.chemin_base)
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["libelle"], "Statuts mis à jour")
        self.assertEqual(
            lire_document_inpi("acte-1", "acte", self.chemin_base)["siren"],
            "542051180",
        )

    def test_enregistre_dedoublonne_et_traite_une_alerte(self):
        changement = Changement(
            champ="statut", libelle="Statut", ancienne_valeur="Active",
            nouvelle_valeur="Radiée", niveau="critique",
            categorie="cessation_radiation",
            regle="statut de cessation ou radiation",
        )
        date_detection = datetime(2026, 8, 3, 7, 5)

        premier = enregistrer_alertes(
            "542051180", [changement], source="INSEE",
            date_detection=date_detection, chemin=self.chemin_base,
        )
        doublon = enregistrer_alertes(
            "542051180", [changement], source="BODACC",
            date_detection=date_detection, chemin=self.chemin_base,
        )
        alertes = lire_alertes(
            niveau="critique", statut="nouvelle", chemin=self.chemin_base
        )

        self.assertEqual((premier, doublon), (1, 0))
        self.assertEqual(len(alertes), 1)
        self.assertEqual(alertes[0]["categorie"], "cessation_radiation")
        changer_statut_alerte(
            alertes[0]["identifiant"], "traitee", self.chemin_base
        )
        self.assertEqual(
            lire_alertes(statut="traitee", chemin=self.chemin_base)[0]["statut"],
            "traitee",
        )

    def test_preferences_filtrent_l_alerte_sans_supprimer_le_changement(self):
        self.assertIn(
            "capital", lire_preferences_alertes("542051180", self.chemin_base)
        )
        configurer_preferences_alertes(
            "542051180", {"dirigeant"}, self.chemin_base
        )
        changement = Changement(
            champ="capital", libelle="Capital", ancienne_valeur="100 €",
            nouvelle_valeur="200 €", niveau="important", categorie="capital",
            regle="modification du capital",
        )

        ajoutees = enregistrer_alertes(
            "542051180", [changement], chemin=self.chemin_base
        )

        self.assertEqual(ajoutees, 0)
        self.assertEqual(lire_alertes(chemin=self.chemin_base), [])

    def test_cycle_de_vie_execution_globale(self):
        identifiant = demarrer_execution_veille(
            "hebdomadaire", "pappers", self.chemin_base
        )
        terminer_execution_veille(
            identifiant, "succes", societes=4, modifications=2, erreurs=1,
            rapport="synthese.html", chemin=self.chemin_base,
        )
        executions = lire_executions_veille(20, self.chemin_base)
        self.assertEqual(len(executions), 1)
        self.assertEqual(executions[0]["statut"], "succes")
        self.assertEqual(executions[0]["societes"], 4)
        self.assertEqual(executions[0]["modifications"], 2)
        self.assertEqual(executions[0]["rapport"], "synthese.html")

    def test_initialiser_base_cree_la_table_collectes(self):
        initialiser_base(self.chemin_base)

        with closing(sqlite3.connect(self.chemin_base)) as connexion:
            table = connexion.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name = 'collectes'
                """
            ).fetchone()

        self.assertEqual(table, ("collectes",))

    def test_migration_25_vers_37_preserve_les_donnees(self):
        ancienne_base = Path(self.dossier_temporaire.name) / "ancienne.sqlite"
        with closing(sqlite3.connect(ancienne_base)) as connexion, connexion:
            connexion.execute(
                "CREATE TABLE donnees_existantes (id INTEGER PRIMARY KEY, valeur TEXT)"
            )
            connexion.execute(
                "INSERT INTO donnees_existantes(valeur) VALUES ('à préserver')"
            )
            connexion.execute("PRAGMA user_version = 25")

        initialiser_base(ancienne_base)

        with closing(sqlite3.connect(ancienne_base)) as connexion:
            self.assertEqual(
                connexion.execute("PRAGMA user_version").fetchone()[0], 37
            )
            self.assertEqual(
                connexion.execute(
                    "SELECT valeur FROM donnees_existantes"
                ).fetchone()[0],
                "à préserver",
            )
            self.assertEqual(
                connexion.execute("PRAGMA integrity_check").fetchone()[0], "ok"
            )

    def test_enregistrer_etat_tache_conserve_le_cycle_de_vie(self):
        enregistrer_etat_tache(
            "123456789",
            "nouvelle_tentative",
            tentative=1,
            message="délai dépassé",
            chemin=self.chemin_base,
        )

        with closing(sqlite3.connect(self.chemin_base)) as connexion:
            ligne = connexion.execute(
                """
                SELECT siren, statut, tentative, message
                FROM taches_collecte
                """
            ).fetchone()

        self.assertEqual(
            ligne,
            ("123456789", "nouvelle_tentative", 1, "délai dépassé"),
        )

    def test_enregistrer_societe_conserve_toutes_les_donnees(self):
        date_collecte = datetime(2026, 7, 29, 19, 30, 0)
        societe = Societe(
            siren="542051180",
            raison_sociale="TOTALENERGIES SE",
            forme_juridique="Société européenne",
            capital="5 704 141 785,00 €",
            statut="Active",
            adresse="92400 COURBEVOIE",
            dirigeant="Patrick Pouyanné",
            derniere_publication_bodacc="10/07/2026",
            dernier_changement="MODIFICATION — Capital",
            source="Pappers",
            provenance={"statut": "INSEE"},
            dates_provenance={"statut": "2026-07-29T19:30:00"},
            erreurs_sources={"INPI": "indisponible"},
            contradictions={"raison_sociale": {"INSEE": "TOTAL", "INPI": "Total"}},
            date_collecte=date_collecte,
        )

        enregistrer_societe(societe, self.chemin_base)

        with closing(sqlite3.connect(self.chemin_base)) as connexion:
            ligne = connexion.execute(
                """
                SELECT
                    siren,
                    raison_sociale,
                    statut,
                    derniere_publication_bodacc,
                    dernier_changement,
                    source,
                    date_collecte
                FROM collectes
                """
            ).fetchone()

        self.assertEqual(
            ligne,
            (
                "542051180",
                "TOTALENERGIES SE",
                "Active",
                "10/07/2026",
                "MODIFICATION — Capital",
                "Pappers",
                "2026-07-29T19:30:00",
            ),
        )
        relue = lire_derniere_collecte("542051180", self.chemin_base)
        self.assertEqual(relue.provenance, {"statut": "INSEE"})
        self.assertEqual(
            relue.dates_provenance, {"statut": "2026-07-29T19:30:00"}
        )
        self.assertEqual(relue.erreurs_sources, {"INPI": "indisponible"})
        self.assertIn("raison_sociale", relue.contradictions)

    def test_enregistrer_societe_conserve_l_historique(self):
        societe = Societe(siren="542051180", statut="Active")

        enregistrer_societe(societe, self.chemin_base)
        societe.statut = "Radiée"
        enregistrer_societe(societe, self.chemin_base)

        with closing(sqlite3.connect(self.chemin_base)) as connexion:
            statuts = connexion.execute(
                """
                SELECT statut
                FROM collectes
                WHERE siren = ?
                ORDER BY id
                """,
                ("542051180",),
            ).fetchall()

        self.assertEqual(statuts, [("Active",), ("Radiée",)])

    def test_lire_derniere_collecte_retourne_le_plus_recent_etat(self):
        premiere = Societe(siren="542051180", statut="Active")
        seconde = Societe(siren="542051180", statut="Radiée")
        enregistrer_societe(premiere, self.chemin_base)
        enregistrer_societe(seconde, self.chemin_base)

        resultat = lire_derniere_collecte(
            "542051180",
            self.chemin_base,
        )

        self.assertIsNotNone(resultat)
        self.assertEqual(resultat.statut, "Radiée")

    def test_lire_derniere_collecte_retourne_none_si_inconnue(self):
        resultat = lire_derniere_collecte(
            "000000000",
            self.chemin_base,
        )

        self.assertIsNone(resultat)

    def test_lire_collectes_societe_retourne_l_historique_dans_l_ordre(self):
        enregistrer_societe(
            Societe(siren="542051180", statut="Active"), self.chemin_base
        )
        enregistrer_societe(
            Societe(siren="542051180", statut="Radiée"), self.chemin_base
        )
        enregistrer_societe(
            Societe(siren="552032534", statut="Active"), self.chemin_base
        )

        historique = lire_collectes_societe(
            "542051180", self.chemin_base
        )

        self.assertEqual(
            [collecte.statut for collecte in historique],
            ["Active", "Radiée"],
        )

    def test_lire_collectes_recentes_applique_la_limite(self):
        enregistrer_societe(
            Societe(siren="542051180", statut="Premier"), self.chemin_base
        )
        enregistrer_societe(
            Societe(siren="552032534", statut="Deuxième"), self.chemin_base
        )

        resultat = lire_collectes_recentes(1, self.chemin_base)

        self.assertEqual(len(resultat), 1)
        self.assertEqual(resultat[0].statut, "Deuxième")
        with self.assertRaises(ValueError):
            lire_collectes_recentes(0, self.chemin_base)

    def test_lire_collectes_entre_et_collecte_avant(self):
        for jour, statut in ((1, "Avant"), (3, "Pendant"), (10, "Après")):
            enregistrer_societe(
                Societe(
                    siren="542051180",
                    statut=statut,
                    date_collecte=datetime(2026, 8, jour, 10),
                ),
                self.chemin_base,
            )

        debut = datetime(2026, 8, 2)
        fin = datetime(2026, 8, 9)
        collectes = lire_collectes_entre(debut, fin, self.chemin_base)
        precedente = lire_collecte_avant(
            "542051180", debut, self.chemin_base
        )

        self.assertEqual([c.statut for c in collectes], ["Pendant"])
        self.assertEqual(precedente.statut, "Avant")
        with self.assertRaises(ValueError):
            lire_collectes_entre(fin, debut, self.chemin_base)

    def test_lire_erreurs_taches_entre(self):
        enregistrer_etat_tache(
            "123456789", "echec", message="API indisponible",
            chemin=self.chemin_base,
        )
        maintenant = datetime.now()

        erreurs = lire_erreurs_taches_entre(
            maintenant.replace(hour=0, minute=0, second=0, microsecond=0),
            maintenant.replace(hour=23, minute=59, second=59, microsecond=999999),
            self.chemin_base,
        )

        self.assertEqual(erreurs, [("123456789", "API indisponible")])

    def test_configuration_et_publications_notion(self):
        configurer_cible_notion(
            "rapports_veille", "collection://veille", self.chemin_base
        )
        configurer_cible_notion(
            "rapports_veille", "collection://nouvelle", self.chemin_base
        )

        self.assertEqual(
            lire_cible_notion("rapports_veille", self.chemin_base),
            "collection://nouvelle",
        )
        self.assertFalse(
            publication_notion_existe("rapport-1", self.chemin_base)
        )
        enregistrer_publication_notion(
            "rapport-1", "page-1", "https://notion.test/page-1",
            self.chemin_base,
        )
        self.assertTrue(
            publication_notion_existe("rapport-1", self.chemin_base)
        )
        with self.assertRaises(sqlite3.IntegrityError):
            enregistrer_publication_notion(
                "rapport-1", "page-2", "https://notion.test/page-2",
                self.chemin_base,
            )


if __name__ == "__main__":
    unittest.main()
