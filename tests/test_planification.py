import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from modules.planification import (
    construire_xml_tache, lancer_tache, lire_etat_tache, prochaine_limite,
)


class TestPlanification(unittest.TestCase):
    def test_prochaine_limite_lundi(self):
        self.assertEqual(
            prochaine_limite(7, datetime(2026, 8, 2, 11, 0)),
            "2026-08-03T07:00:00",
        )
        self.assertEqual(
            prochaine_limite(7, datetime(2026, 8, 3, 8, 0)),
            "2026-08-10T07:00:00",
        )
        self.assertEqual(
            prochaine_limite(9, datetime(2026, 8, 2, 11, 0), 2, 30),
            "2026-08-05T09:30:00",
        )

    def test_xml_active_le_rattrapage_et_empeche_le_chevauchement(self):
        xml = construire_xml_tache(
            Path("C:/Python/python.exe"),
            Path("D:/Veille-SIREN"),
            utilisateur="gilda",
        )
        self.assertIn("<Monday />", xml)
        self.assertIn("<StartWhenAvailable>true</StartWhenAvailable>", xml)
        self.assertIn("<MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>", xml)
        self.assertIn("<WakeToRun>true</WakeToRun>", xml)
        self.assertIn("<RestartOnFailure>", xml)
        self.assertIn("<RunLevel>LeastPrivilege</RunLevel>", xml)
        self.assertIn("--execution-hebdomadaire", xml)
        self.assertIn("--sans-interface", xml)

    @patch("modules.planification.subprocess.run")
    def test_lire_etat_tache(self, mock_run):
        mock_run.return_value = Mock(stdout=(
            '{"Etat":"Ready","Derniere":"2026-08-01T07:00:00",'
            '"Prochaine":"2026-08-03T07:00:00","Resultat":0}'
        ))
        etat = lire_etat_tache()
        self.assertTrue(etat["disponible"])
        self.assertEqual(etat["etat"], "Ready")
        self.assertEqual(etat["resultat"], 0)

    @patch("modules.planification.subprocess.run")
    def test_lancer_tache(self, mock_run):
        lancer_tache()
        arguments = mock_run.call_args.args[0]
        self.assertEqual(arguments[:2], ["schtasks", "/Run"])
        self.assertTrue(mock_run.call_args.kwargs["check"])


if __name__ == "__main__":
    unittest.main()
