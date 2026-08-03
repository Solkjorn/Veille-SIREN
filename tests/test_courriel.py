import tempfile
import unittest
from datetime import date
from pathlib import Path

from modules.comparaison import Changement
from modules.courriel import (
    ErreurCourriel, envoyer_alerte_critique, envoyer_synthese,
    verifier_connexion_smtp,
)


class _SMTP:
    instance = None

    def __init__(self, hote, port, timeout):
        self.hote, self.port, self.timeout = hote, port, timeout
        self.message = None
        _SMTP.instance = self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def starttls(self):
        self.tls = True

    def login(self, utilisateur, mot_de_passe):
        self.identifiants = (utilisateur, mot_de_passe)

    def send_message(self, message):
        self.message = message


class TestCourriel(unittest.TestCase):
    def test_verifie_la_connexion_sans_envoyer_de_message(self):
        configuration = {
            "hote": "smtp.test", "port": "587", "utilisateur": "user",
            "mot_de_passe": "secret", "expediteur": "a@test.fr",
            "destinataire": "b@test.fr",
        }

        self.assertTrue(verifier_connexion_smtp(configuration, client=_SMTP))
        self.assertTrue(_SMTP.instance.tls)
        self.assertEqual(_SMTP.instance.identifiants, ("user", "secret"))
        self.assertIsNone(_SMTP.instance.message)

    def test_envoyer_synthese_html(self):
        with tempfile.TemporaryDirectory() as dossier:
            rapport = Path(dossier) / "synthese.html"
            rapport.write_text("<h1>Synthèse</h1>", encoding="utf-8")
            configuration = {
                "hote": "smtp.test", "port": "587", "utilisateur": "user",
                "mot_de_passe": "secret", "expediteur": "a@test.fr",
                "destinataire": "b@test.fr",
            }
            envoyer_synthese(
                rapport, configuration, client=_SMTP,
                date_reference=date(2026, 8, 3),
            )
            self.assertTrue(_SMTP.instance.tls)
            self.assertEqual(_SMTP.instance.message["To"], "b@test.fr")
            self.assertEqual(
                _SMTP.instance.message["Subject"],
                "Synthèse hebdomadaire Veille-SIREN — 03/08/2026",
            )
            self.assertIn("text/html", str(_SMTP.instance.message))

    def test_envoyer_synthese_accepte_un_destinataire_de_portefeuille(self):
        with tempfile.TemporaryDirectory() as dossier:
            rapport = Path(dossier) / "portefeuille.html"
            rapport.write_text("<h1>Clients</h1>", encoding="utf-8")
            configuration = {
                "hote": "smtp.test", "port": "587", "utilisateur": "user",
                "mot_de_passe": "secret", "expediteur": "a@test.fr",
                "destinataire": "general@test.fr",
            }
            envoyer_synthese(
                rapport, configuration, client=_SMTP,
                destinataire="clients@test.fr", objet="Veille — Clients",
            )
            self.assertEqual(_SMTP.instance.message["To"], "clients@test.fr")
            self.assertEqual(_SMTP.instance.message["Subject"], "Veille — Clients")

    def test_refuse_une_configuration_absente(self):
        with self.assertRaisesRegex(ErreurCourriel, "Aucune configuration"):
            envoyer_synthese(Path("inconnu.html"), configuration={})

    def test_envoyer_alerte_critique(self):
        configuration = {
            "hote": "smtp.test", "port": "587", "utilisateur": "user",
            "mot_de_passe": "secret", "expediteur": "a@test.fr",
            "destinataire": "b@test.fr",
        }
        changement = Changement(
            "statut", "Statut", "Active", "Radiée", niveau="critique",
            categorie="cessation_radiation", regle="radiation détectée",
        )
        envoyer_alerte_critique(
            "542051180", "Société test", changement,
            configuration=configuration, client=_SMTP,
        )
        message = _SMTP.instance.message
        self.assertIn("Alerte critique", message["Subject"])
        self.assertIn("radiation détectée", message.get_body().get_content())


if __name__ == "__main__":
    unittest.main()
