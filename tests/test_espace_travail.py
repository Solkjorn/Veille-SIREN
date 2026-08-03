import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from modules.espace_travail import (
    ajouter_echeance, ajouter_lien_societes, ajouter_note, ajouter_tache,
    appliquer_profil_societe, changer_statut_tache, enregistrer_generation,
    enregistrer_modele_rapport, enregistrer_progression_demarrage,
    enregistrer_regle, epingler_note, evaluer_regle, exporter_echeances_ics,
    exporter_taches_csv, generation_deja_enregistree, lire_echeances,
    lire_liens_societe, lire_modeles_rapports, lire_notes, lire_profil_societe,
    lire_profils, lire_progression_demarrage, lire_regles, lire_taches,
    simuler_regle,
)
from modules.modele import Societe


class TestEspaceTravail(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name) / "espace.sqlite"

    def tearDown(self):
        self.temp.cleanup()

    def test_assistant_reprend_sa_progression(self):
        self.assertTrue(lire_progression_demarrage(self.base)["base_neuve"])
        enregistrer_progression_demarrage(4, False, self.base)
        self.assertEqual(lire_progression_demarrage(self.base)["etape"], 4)
        enregistrer_progression_demarrage(6, True, self.base)
        self.assertTrue(lire_progression_demarrage(self.base)["termine"])

    def test_profils_preconfigures_et_application(self):
        self.assertEqual([p["code"] for p in lire_profils(self.base)], ["standard", "renforce", "critique"])
        profil = appliquer_profil_societe("542051180", "critique", chemin=self.base)
        self.assertEqual(profil["notification"], "immediate")
        self.assertEqual(lire_profil_societe("542051180", self.base)["code"], "critique")

    def test_calendrier_et_export_ics(self):
        ajouter_echeance("Assemblée", "2026-09-15", "542051180", responsable="Gildas", chemin=self.base)
        echeances = lire_echeances(chemin=self.base)
        contenu = exporter_echeances_ics(echeances)
        self.assertIn("DTSTART;VALUE=DATE:20260915", contenu)
        self.assertIn("SUMMARY:Assemblée", contenu)

    def test_tache_historisee_et_exportee(self):
        identifiant = ajouter_tache("Vérifier l'acte", "542051180", priorite="haute", chemin=self.base)
        changer_statut_tache(identifiant, "en_cours", self.base)
        tache = lire_taches(siren="542051180", chemin=self.base)[0]
        self.assertEqual(tache["statut"], "en_cours")
        self.assertIn("Vérifier l'acte", exporter_taches_csv([tache]))

    def test_notes_epinglees_et_liens(self):
        identifiant = ajouter_note("Contexte confidentiel", "542051180", chemin=self.base)
        epingler_note(identifiant, True, self.base)
        self.assertTrue(lire_notes(siren="542051180", chemin=self.base)[0]["epinglee"])
        ajouter_lien_societes("542051180", "552100554", "Filiale", self.base)
        self.assertEqual(lire_liens_societe("542051180", self.base)[0]["libelle"], "Filiale")

    def test_regle_versionnee_simulee_sans_alerte(self):
        enregistrer_regle("Radiation", "statut", "egal", "radiée", "critique", "Radiation", chemin=self.base)
        regle = lire_regles(self.base)[0]
        ancienne = Societe("542051180", statut="Active")
        nouvelle = Societe("542051180", statut="Radiée")
        self.assertTrue(evaluer_regle(regle, ancienne, nouvelle))
        self.assertEqual(simuler_regle(regle, [ancienne, nouvelle]), [nouvelle])

    def test_modeles_et_anti_doublon_generation(self):
        identifiant = enregistrer_modele_rapport("Clients", None, 7, ["critique"], ["resume"], "html", "hebdomadaire", "", True, self.base)
        self.assertEqual(lire_modeles_rapports(self.base)[0]["nom"], "Clients")
        instant = datetime(2026, 8, 3, 7)
        self.assertTrue(enregistrer_generation(identifiant, "succes", date_reference=instant, chemin=self.base))
        self.assertTrue(generation_deja_enregistree(identifiant, date_reference=instant, chemin=self.base))
        self.assertFalse(enregistrer_generation(identifiant, "succes", date_reference=instant, chemin=self.base))


if __name__ == "__main__":
    unittest.main()
