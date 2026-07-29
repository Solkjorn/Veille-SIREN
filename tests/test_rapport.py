import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from modules.comparaison import Changement
from modules.modele import Societe
from modules.rapport import formater_valeur, generer_rapport


class TestRapport(unittest.TestCase):

    def test_formater_valeur_protege_les_tableaux_markdown(self):
        self.assertEqual(
            formater_valeur("Président | Directeur\nGénéral"),
            r"Président \| Directeur Général",
        )
        self.assertEqual(formater_valeur(""), "—")

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

        self.assertEqual(chemin.name, "veille_20260729_201530.md")
        self.assertIn("TOTALENERGIES SE (542051180)", contenu)
        self.assertIn("| Capital | 100 000 € | 120 000 € |", contenu)

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

        self.assertIn("Aucun changement détecté.", contenu)


if __name__ == "__main__":
    unittest.main()
