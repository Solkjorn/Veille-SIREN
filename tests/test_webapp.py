import tempfile
import unittest
from datetime import datetime
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook

from modules.base_donnees import enregistrer_societe
from modules.modele import Societe
from modules.societes_surveillees import (
    ajouter_societe_surveillee,
    supprimer_societe_surveillee,
)
from webapp import creer_application


class TestApplicationWeb(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name) / "web.sqlite"
        self.application = creer_application({
            "TESTING": True,
            "BASE_SQLITE": self.base,
            "CSRF_ACTIVE": False,
        })
        self.client = self.application.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def test_tableau_de_bord_vide(self):
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("Aucune société", reponse.get_data(as_text=True))

    def test_tableau_de_bord_affiche_les_societes_et_indicateurs(self):
        ajouter_societe_surveillee(
            "542051180", commentaire="Active", chemin=self.base
        )
        enregistrer_societe(
            Societe(
                siren="542051180",
                raison_sociale="TOTALENERGIES SE",
                forme_juridique="Société européenne",
                capital="5 704 141 785 €",
                statut="Active",
                adresse="Courbevoie",
                dirigeant="Direction générale",
                derniere_publication_bodacc="10/07/2026",
                dernier_changement="Modification du capital",
                date_collecte=datetime(2026, 7, 30, 20, 0),
            ),
            self.base,
        )
        ajouter_societe_surveillee(
            "552032534", actif=False, commentaire="Inactive", chemin=self.base
        )
        ajouter_societe_surveillee("304154719", chemin=self.base)
        supprimer_societe_surveillee("304154719", chemin=self.base)

        reponse = self.client.get("/")
        page = reponse.get_data(as_text=True)

        self.assertEqual(reponse.status_code, 200)
        for texte in ("542051180", "552032534", "304154719",
                      "Active", "Inactive", "Archivée", "TOTALENERGIES SE",
                      "Modification du capital", "Mini-rapport"):
            self.assertIn(texte, page)
        self.assertIn("<th>Dernière modification</th>", page)
        self.assertIn("10/07/2026", page)
        self.assertIn('class="objet-modification"', page)
        self.assertIn('id="rapport-542051180"', page)
        self.assertIn('aria-expanded="false"', page)

    def test_ajoute_modifie_et_change_l_etat_d_une_societe(self):
        reponse = self.client.post("/societes", data={
            "siren": "542051180",
            "actif": "1",
            "commentaire": "À suivre",
        })
        self.assertEqual(reponse.status_code, 302)

        self.client.post("/societes/542051180/modifier", data={
            "commentaire": "Commentaire modifié",
        })
        self.client.post("/societes/542051180/desactiver")
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn("Commentaire modifié", page)
        self.assertIn("Inactive", page)

        self.client.post("/societes/542051180/activer")
        self.client.post("/societes/542051180/archiver")
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn("Archivée", page)
        self.assertIn("Restaurer la société", page)

        self.client.post("/societes/542051180/restaurer")
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn("Active", page)

    def test_protege_les_actions_avec_un_jeton_csrf(self):
        application = creer_application({
            "TESTING": True,
            "BASE_SQLITE": self.base,
            "SECRET_KEY": "test",
        })
        reponse = application.test_client().post("/societes", data={
            "siren": "542051180",
        })
        self.assertEqual(reponse.status_code, 400)

    def test_previsualise_puis_confirme_un_import_excel(self):
        classeur = Workbook()
        feuille = classeur.active
        feuille.title = "Societes"
        feuille.append(["SIREN", "Actif", "Commentaire"])
        feuille.append(["542051180", "Oui", "Importée"])
        feuille.append(["123", "Oui", "Invalide"])
        contenu = BytesIO()
        classeur.save(contenu)
        classeur.close()
        contenu.seek(0)

        reponse = self.client.post(
            "/import-excel/previsualiser",
            data={"fichier_excel": (contenu, "societes.xlsx")},
            content_type="multipart/form-data",
        )
        page = reponse.get_data(as_text=True)

        self.assertEqual(reponse.status_code, 200)
        self.assertIn("Prévisualisation", page)
        self.assertIn("542051180", page)
        self.assertIn("SIREN invalide", page)
        marqueur = 'name="identifiant_import"\n               value="'
        debut = page.index(marqueur) + len(marqueur)
        identifiant = page[debut:page.index('"', debut)]

        confirmation = self.client.post(
            "/import-excel/confirmer",
            data={"identifiant_import": identifiant},
            follow_redirects=True,
        )
        page_finale = confirmation.get_data(as_text=True)

        self.assertIn("Import terminé", page_finale)
        self.assertIn("Importée", page_finale)

    def test_refuse_une_confirmation_d_import_expiree(self):
        reponse = self.client.post(
            "/import-excel/confirmer",
            data={"identifiant_import": "inconnu"},
            follow_redirects=True,
        )
        self.assertIn(
            "prévisualisation a expiré", reponse.get_data(as_text=True)
        )

    def test_affiche_l_historique_et_les_changements_d_une_societe(self):
        ajouter_societe_surveillee("542051180", chemin=self.base)
        enregistrer_societe(
            Societe(
                siren="542051180",
                raison_sociale="SOCIÉTÉ TEST",
                capital="100 000 €",
                statut="Active",
                date_collecte=datetime(2026, 7, 29, 10, 0),
            ),
            self.base,
        )
        enregistrer_societe(
            Societe(
                siren="542051180",
                raison_sociale="SOCIÉTÉ TEST",
                capital="120 000 €",
                statut="Active",
                date_collecte=datetime(2026, 7, 30, 10, 0),
            ),
            self.base,
        )

        reponse = self.client.get("/societes/542051180/historique")
        page = reponse.get_data(as_text=True)

        self.assertEqual(reponse.status_code, 200)
        self.assertIn("Historique des collectes", page)
        self.assertIn("29/07/2026 à 10:00", page)
        self.assertIn("30/07/2026 à 10:00", page)
        self.assertIn("Capital", page)
        self.assertIn("100 000 €", page)
        self.assertIn("120 000 €", page)

    def test_historique_retourne_404_pour_un_siren_inconnu(self):
        self.assertEqual(
            self.client.get("/societes/542051180/historique").status_code,
            404,
        )


if __name__ == "__main__":
    unittest.main()
