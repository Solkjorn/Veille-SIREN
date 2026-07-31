import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime
from pathlib import Path

from modules.base_donnees import (
    enregistrer_etat_tache,
    enregistrer_societe,
    initialiser_base,
    lire_collectes_societe,
    lire_collectes_recentes,
    lire_derniere_collecte,
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


if __name__ == "__main__":
    unittest.main()
