import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from modules.base_donnees import (
    configurer_cible_notion,
    publication_notion_existe,
)
from modules.notion import (
    ErreurNotion,
    normaliser_identifiant_notion,
    publier_rapport_developpement,
    publier_rapport_veille,
    publier_synthese_hebdomadaire,
    verifier_connexion_notion,
)


class _Reponse:
    def __init__(self, donnees):
        self.donnees = json.dumps(donnees).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.donnees


class TestNotion(unittest.TestCase):
    def test_normaliser_identifiant_de_connecteur(self):
        self.assertEqual(
            normaliser_identifiant_notion("collection://cible-1"), "cible-1"
        )

    def test_verifier_connexion_utilise_le_jeton(self):
        requetes = []

        def ouvrir(requete, timeout):
            requetes.append((requete, timeout))
            return _Reponse({"id": "bot-1", "name": "Veille-SIREN"})

        resultat = verifier_connexion_notion("secret_test", ouvre=ouvrir)

        self.assertEqual(resultat["id"], "bot-1")
        self.assertEqual(requetes[0][1], 30)
        self.assertEqual(
            requetes[0][0].get_header("Authorization"), "Bearer secret_test"
        )

    def test_verifier_connexion_refuse_un_jeton_absent(self):
        with self.assertRaisesRegex(ErreurNotion, "Aucun jeton"):
            verifier_connexion_notion("   ")

    def test_publier_rapport_et_empecher_le_doublon(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin_base = Path(dossier) / "veille.sqlite"
            rapport = Path(dossier) / "veille_20260801_120000.html"
            rapport.write_text("<html></html>", encoding="utf-8")
            horodatage = datetime(2026, 8, 1, 12, 0).timestamp()
            rapport.touch()
            import os
            os.utime(rapport, (horodatage, horodatage))
            configurer_cible_notion(
                "rapports_veille", "collection://cible-1", chemin_base
            )
            requetes = []

            def ouvrir(requete, timeout):
                requetes.append(json.loads(requete.data.decode("utf-8")))
                return _Reponse({
                    "id": "page-1",
                    "url": "https://notion.test/page-1",
                })

            url = publier_rapport_veille(
                rapport,
                [(object(), [object()]), (object(), [])],
                [("123456789", "Erreur")],
                chemin_base,
                jeton="secret_test",
                ouvre=ouvrir,
            )

            self.assertEqual(url, "https://notion.test/page-1")
            self.assertEqual(requetes[0]["parent"]["data_source_id"], "cible-1")
            self.assertEqual(requetes[0]["properties"]["Sociétés"]["number"], 2)
            self.assertEqual(requetes[0]["properties"]["Modifications"]["number"], 1)
            self.assertTrue(
                publication_notion_existe(rapport.stem, chemin_base)
            )
            self.assertIsNone(
                publier_rapport_veille(
                    rapport, [], chemin_base=chemin_base,
                    jeton="secret_test", ouvre=ouvrir
                )
            )
            self.assertEqual(len(requetes), 1)

    def test_publier_rapport_developpement(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin_base = Path(dossier) / "veille.sqlite"
            rapport = Path(dossier) / "developpement_20260802.md"
            rapport.write_text(
                "# Rapport journalier\n\n## Travaux réalisés\n\n- Ajout Notion\n",
                encoding="utf-8",
            )
            configurer_cible_notion(
                "rapports_developpement", "collection://journal-1", chemin_base
            )
            requetes = []

            def ouvrir(requete, timeout):
                requetes.append(json.loads(requete.data.decode("utf-8")))
                return _Reponse({
                    "id": "page-dev-1",
                    "url": "https://notion.test/page-dev-1",
                })

            url = publier_rapport_developpement(
                rapport, chemin_base, jeton="secret_test", ouvre=ouvrir
            )

            self.assertEqual(url, "https://notion.test/page-dev-1")
            donnees = requetes[0]
            self.assertEqual(
                donnees["parent"]["data_source_id"], "journal-1"
            )
            self.assertEqual(
                donnees["properties"]["Compte rendu"]["title"][0]
                ["text"]["content"],
                "Compte rendu — 2 août 2026",
            )
            self.assertEqual(donnees["children"][0]["type"], "heading_2")
            self.assertTrue(
                publication_notion_existe(rapport.stem, chemin_base)
            )

    def test_refuser_un_nom_de_rapport_developpement_invalide(self):
        with self.assertRaisesRegex(ValueError, "developpement_YYYYMMDD"):
            publier_rapport_developpement(Path("rapport.md"), jeton="test")

    def test_publier_synthese_hebdomadaire(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin_base = Path(dossier) / "veille.sqlite"
            rapport = Path(dossier) / "synthese_hebdomadaire_20260803_070000.html"
            rapport.write_text(
                "<strong>4</strong>réussies <strong>2</strong>modifiées "
                "<strong>1</strong>erreurs",
                encoding="utf-8",
            )
            configurer_cible_notion(
                "rapports_veille", "collection://veille-1", chemin_base
            )
            requetes = []

            def ouvrir(requete, timeout):
                requetes.append(json.loads(requete.data.decode("utf-8")))
                return _Reponse({
                    "id": "page-synthese-1",
                    "url": "https://notion.test/page-synthese-1",
                })

            url = publier_synthese_hebdomadaire(
                rapport, chemin_base, jeton="secret_test", ouvre=ouvrir
            )

            self.assertEqual(url, "https://notion.test/page-synthese-1")
            proprietes = requetes[0]["properties"]
            self.assertEqual(proprietes["Type"]["select"]["name"], "Hebdomadaire")
            self.assertEqual(proprietes["Sociétés"]["number"], 4)
            self.assertEqual(proprietes["Modifications"]["number"], 2)
            self.assertEqual(proprietes["Erreurs"]["number"], 1)


if __name__ == "__main__":
    unittest.main()
