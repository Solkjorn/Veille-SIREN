import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime
from pathlib import Path

from modules.base_donnees import (
    configurer_cible_notion,
    enregistrer_etat_tache,
    enregistrer_publication_notion,
    enregistrer_societe,
    initialiser_base,
    lire_collectes_societe,
    lire_collectes_recentes,
    lire_collectes_entre,
    lire_collecte_avant,
    lire_derniere_collecte,
    lire_erreurs_taches_entre,
    lire_cible_notion,
    publication_notion_existe,
)
from modules.modele import Societe


class TestBaseDonnees(unittest.TestCase):

    def setUp(self):
        self.dossier_temporaire = tempfile.TemporaryDirectory()
        self.chemin_base = (
            Path(self.dossier_temporaire.name) / "veille_test.sqlite"
        )

    def tearDown(self):
        self.dossier_temporaire.cleanup()

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
