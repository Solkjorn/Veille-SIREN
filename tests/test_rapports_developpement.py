import unittest
from pathlib import Path


RACINE = Path(__file__).parents[1]
DOSSIER_RAPPORTS = RACINE / "rapports"
SECTIONS_REQUISES = (
    "## Temps",
    "## Travaux réalisés",
    "## Modules concernés",
    "## Vérifications",
    "## Difficultés et décisions",
    "## Commit associé",
    "## Prochaine étape",
)


class TestRapportsDeveloppement(unittest.TestCase):
    def test_tous_les_rapports_suivent_la_structure_convenue(self):
        rapports = sorted(DOSSIER_RAPPORTS.glob("developpement_*.md"))
        self.assertTrue(rapports)

        for rapport in rapports:
            with self.subTest(rapport=rapport.name):
                contenu = rapport.read_text(encoding="utf-8")
                for section in SECTIONS_REQUISES:
                    self.assertIn(section, contenu)
                self.assertIn("session", contenu.casefold())


if __name__ == "__main__":
    unittest.main()
