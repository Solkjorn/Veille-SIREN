import json
import sqlite3
import tempfile
import unittest
import zipfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from modules.sauvegarde import (
    ErreurSauvegarde, creer_sauvegarde, verifier_restauration,
)


class TestSauvegarde(unittest.TestCase):
    def setUp(self):
        self.temporaire = tempfile.TemporaryDirectory()
        self.racine = Path(self.temporaire.name)
        self.base = self.racine / "donnees" / "veille.sqlite"
        self.rapports = self.racine / "rapports"
        self.secrets = self.racine / "secrets"
        self.destination = self.racine / "sauvegardes"
        self.base.parent.mkdir()
        self.rapports.mkdir()
        self.secrets.mkdir()
        with closing(sqlite3.connect(self.base)) as connexion:
            with connexion:
                connexion.execute("CREATE TABLE exemple (valeur TEXT)")
                connexion.execute("INSERT INTO exemple VALUES ('préservée')")
        (self.rapports / "rapport.html").write_text("<h1>Rapport</h1>", encoding="utf-8")
        (self.secrets / "notion-token.bin").write_bytes(b"donnees-dpapi")

    def tearDown(self):
        self.temporaire.cleanup()

    def test_cree_une_archive_verifiee_et_complete(self):
        archive = creer_sauvegarde(
            chemin_base=self.base,
            dossier_rapports=self.rapports,
            dossier_secrets=self.secrets,
            dossier_destination=self.destination,
            date_sauvegarde=datetime(2026, 8, 2, 13, 0),
        )
        with zipfile.ZipFile(archive) as contenu:
            self.assertIsNone(contenu.testzip())
            self.assertIn("donnees/veille.sqlite", contenu.namelist())
            self.assertIn("rapports/rapport.html", contenu.namelist())
            self.assertIn("secrets/notion-token.bin", contenu.namelist())
            manifeste = json.loads(contenu.read("manifest.json"))
            self.assertEqual(manifeste["application"], "Veille-SIREN")

    def test_applique_la_retention(self):
        for index in range(3):
            creer_sauvegarde(
                chemin_base=self.base,
                dossier_rapports=self.rapports,
                dossier_secrets=self.secrets,
                dossier_destination=self.destination,
                date_sauvegarde=datetime(2026, 8, 1) + timedelta(seconds=index),
                conserver=2,
            )
        self.assertEqual(len(list(self.destination.glob("*.zip"))), 2)

    def test_refuse_une_base_absente(self):
        with self.assertRaises(ErreurSauvegarde):
            creer_sauvegarde(
                chemin_base=self.racine / "absente.sqlite",
                dossier_destination=self.destination,
            )

    def test_verifie_une_restauration_sqlite_isolee(self):
        archive = creer_sauvegarde(
            chemin_base=self.base,
            dossier_rapports=self.rapports,
            dossier_secrets=self.secrets,
            dossier_destination=self.destination,
        )
        bilan = verifier_restauration(archive)
        self.assertEqual(bilan["integrite"], "ok")
        self.assertGreaterEqual(bilan["tables"], 1)

    def test_refuse_une_archive_incomplete(self):
        archive = self.racine / "incomplete.zip"
        with zipfile.ZipFile(archive, "w") as contenu:
            contenu.writestr("manifest.json", '{"application":"Veille-SIREN"}')
        with self.assertRaises(ErreurSauvegarde):
            verifier_restauration(archive)


if __name__ == "__main__":
    unittest.main()
