import tempfile
import unittest
import os
from datetime import datetime
from pathlib import Path

from modules.comparaison import Changement
from modules.modele import Societe
from modules.base_donnees import enregistrer_societe
from modules.rapport import (
    formater_html,
    formater_valeur,
    generer_rapport,
    generer_synthese_hebdomadaire,
    generer_synthese_portefeuille,
    nettoyer_rapports_anciens,
)


class TestRapport(unittest.TestCase):

    def test_synthese_portefeuille_ne_contient_que_ses_societes(self):
        with tempfile.TemporaryDirectory() as dossier:
            base = Path(dossier) / "veille.sqlite"
            rapports = Path(dossier) / "rapports"
            for siren, nom in (("111111111", "CLIENT"), ("222222222", "AUTRE")):
                enregistrer_societe(
                    Societe(siren=siren, raison_sociale=nom), base
                )
            chemin = generer_synthese_portefeuille(
                "Clients", ["111111111"], base, rapports
            )
            contenu = chemin.read_text(encoding="utf-8")
            self.assertIn("CLIENT", contenu)
            self.assertNotIn("AUTRE", contenu)

    def test_formater_valeur_protege_les_tableaux_markdown(self):
        self.assertEqual(
            formater_valeur("Président | Directeur\nGénéral"),
            r"Président \| Directeur Général",
        )
        self.assertEqual(formater_valeur(""), "—")
        self.assertEqual(formater_html("<script>"), "&lt;script&gt;")

    def test_generer_rapport_inclut_societe_et_changements(self):
        societe = Societe(
            siren="542051180",
            raison_sociale="TOTALENERGIES SE",
            statut="Active",
            capital="120 000 €",
            source="Pappers",
        )
        changements = [
            Changement(
                champ="capital",
                libelle="Capital",
                ancienne_valeur="100 000 €",
                nouvelle_valeur="120 000 €",
                niveau="important",
                categorie="capital",
                regle="modification du capital",
            )
        ]
        date_rapport = datetime(2026, 7, 29, 20, 15, 30)

        with tempfile.TemporaryDirectory() as dossier:
            chemin = generer_rapport(
                [(societe, changements)],
                dossier=Path(dossier),
                date_rapport=date_rapport,
            )
            contenu = chemin.read_text(encoding="utf-8")
            self.assertIn("Important", contenu)
            markdown_existe = (
                Path(dossier) / "veille_20260729_201530.md"
            ).is_file()

        self.assertEqual(chemin.name, "veille_20260729_201530.html")
        self.assertIn("TOTALENERGIES SE (542051180)", contenu)
        self.assertIn("Sociétés modifiées", contenu)
        self.assertIn("100 000 €", contenu)
        self.assertIn("120 000 €", contenu)
        self.assertTrue(markdown_existe)

    def test_generer_rapport_indique_l_absence_de_changement(self):
        societe = Societe(
            siren="542051180",
            raison_sociale="TOTALENERGIES SE",
        )

        with tempfile.TemporaryDirectory() as dossier:
            chemin = generer_rapport(
                [(societe, [])],
                dossier=Path(dossier),
            )
            contenu = chemin.read_text(encoding="utf-8")

        self.assertIn("Sociétés sans changement", contenu)
        self.assertIn("Aucun changement détecté.", contenu)

    def test_generer_rapport_resume_les_erreurs(self):
        date_rapport = datetime(2026, 8, 1, 13, 0)
        with tempfile.TemporaryDirectory() as dossier:
            chemin = generer_rapport(
                [],
                dossier=Path(dossier),
                date_rapport=date_rapport,
                erreurs=[("123456789", "Service indisponible")],
            )
            contenu = chemin.read_text(encoding="utf-8")

        self.assertIn("123456789", contenu)
        self.assertIn("Service indisponible", contenu)

    def test_generer_synthese_hebdomadaire_depuis_sqlite(self):
        with tempfile.TemporaryDirectory() as dossier:
            racine = Path(dossier)
            base = racine / "veille.sqlite"
            rapports = racine / "rapports"
            enregistrer_societe(
                Societe(
                    siren="542051180",
                    raison_sociale="SOCIÉTÉ HEBDO",
                    capital="100 000 €",
                    date_collecte=datetime(2026, 7, 24, 10),
                ),
                base,
            )
            enregistrer_societe(
                Societe(
                    siren="542051180",
                    raison_sociale="SOCIÉTÉ HEBDO",
                    capital="120 000 €",
                    source="INPI",
                    date_collecte=datetime(2026, 7, 30, 10),
                ),
                base,
            )

            chemin = generer_synthese_hebdomadaire(
                base,
                rapports,
                date_fin=datetime(2026, 8, 1, 10),
            )
            contenu = chemin.read_text(encoding="utf-8")

        self.assertEqual(
            chemin.name, "synthese_hebdomadaire_20260801_100000.html"
        )
        self.assertIn("Synthèse hebdomadaire", contenu)
        self.assertIn("100 000 €", contenu)
        self.assertIn("120 000 €", contenu)

    def test_nettoyage_ne_supprime_que_les_anciens_rapports_de_veille(self):
        with tempfile.TemporaryDirectory() as dossier:
            racine = Path(dossier)
            ancien = racine / "veille_ancien.html"
            synthese = racine / "synthese_hebdomadaire_ancienne.html"
            developpement = racine / "developpement_ancien.md"
            recent = racine / "veille_recent.html"
            for chemin in (ancien, synthese, developpement, recent):
                chemin.write_text("rapport", encoding="utf-8")
            date_ancienne = datetime(2025, 1, 1).timestamp()
            for chemin in (ancien, synthese, developpement):
                os.utime(chemin, (date_ancienne, date_ancienne))

            supprimes = nettoyer_rapports_anciens(
                racine,
                conservation_jours=365,
                maintenant=datetime(2026, 8, 1),
            )

            self.assertEqual(set(supprimes), {ancien, synthese})
            self.assertTrue(developpement.is_file())
            self.assertTrue(recent.is_file())

    def test_nettoyage_refuse_une_duree_invalide(self):
        with self.assertRaises(ValueError):
            nettoyer_rapports_anciens(conservation_jours=0)


if __name__ == "__main__":
    unittest.main()
