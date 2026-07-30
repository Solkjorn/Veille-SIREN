import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook

from modules.import_excel import (
    analyser_fichier_excel,
    analyser_televersement_excel,
    importer_apercu,
    importer_fichier_excel,
)
from modules.lecture_excel import lire_sirens
from modules.societes_surveillees import (
    ajouter_societe_surveillee,
    lire_societe_surveillee,
    supprimer_societe_surveillee,
)


class TestImportExcel(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dossier = Path(self.temp.name)
        self.fichier = self.dossier / "societes.xlsx"
        self.base = self.dossier / "veille.sqlite"

    def tearDown(self):
        self.temp.cleanup()

    def _creer_classeur(self, lignes, entetes=None, feuille="Societes"):
        classeur = Workbook()
        onglet = classeur.active
        onglet.title = feuille
        onglet.append(entetes or ["SIREN", "Actif", "Commentaire"])
        for ligne in lignes:
            onglet.append(ligne)
        classeur.save(self.fichier)
        classeur.close()

    def test_analyse_normalise_et_ne_modifie_pas_la_base(self):
        self._creer_classeur([
            [542051180, "Oui", " Groupe énergie "],
            ["552 032 534", "non", None],
        ])

        apercu = analyser_fichier_excel(self.fichier)

        self.assertEqual(apercu.erreurs, [])
        self.assertEqual(
            [(ligne.siren, ligne.actif, ligne.commentaire)
             for ligne in apercu.lignes],
            [
                ("542051180", True, "Groupe énergie"),
                ("552032534", False, ""),
            ],
        )
        self.assertFalse(self.base.exists())

    def test_signale_siren_invalide_doublon_et_actif_invalide(self):
        self._creer_classeur([
            ["123", "Oui", ""],
            ["542051180", "Oui", ""],
            ["542051180", "peut-être", ""],
        ])

        apercu = analyser_fichier_excel(self.fichier)

        self.assertEqual([ligne.siren for ligne in apercu.lignes],
                         ["542051180"])
        self.assertEqual(len(apercu.erreurs), 3)
        self.assertEqual({erreur.numero for erreur in apercu.erreurs}, {2, 4})

    def test_refuse_feuille_ou_colonnes_inattendues(self):
        self._creer_classeur([], feuille="Autre")
        with self.assertRaisesRegex(ValueError, "Feuille attendue"):
            analyser_fichier_excel(self.fichier)

        self._creer_classeur([], entetes=["SIREN", "Nom", "Commentaire"])
        with self.assertRaisesRegex(ValueError, "Colonnes attendues"):
            analyser_fichier_excel(self.fichier)

        self._creer_classeur(
            [], entetes=["SIREN", "Actif", "Commentaire", "Inattendue"]
        )
        with self.assertRaisesRegex(ValueError, "Colonnes attendues"):
            analyser_fichier_excel(self.fichier)

    def test_refuse_format_incorrect_ou_fichier_absent(self):
        with self.assertRaisesRegex(ValueError, r"\.xlsx"):
            analyser_fichier_excel(self.dossier / "societes.xls")
        with self.assertRaises(FileNotFoundError):
            analyser_fichier_excel(self.dossier / "absent.xlsx")

    def test_analyse_un_fichier_televerse_sans_l_ecrire(self):
        classeur = Workbook()
        onglet = classeur.active
        onglet.title = "Societes"
        onglet.append(["SIREN", "Actif", "Commentaire"])
        onglet.append(["542051180", "Oui", "Téléversée"])
        contenu = BytesIO()
        classeur.save(contenu)
        classeur.close()

        apercu = analyser_televersement_excel(
            "../../societes.xlsx", contenu.getvalue()
        )

        self.assertEqual(len(apercu.lignes), 1)
        self.assertEqual(apercu.lignes[0].commentaire, "Téléversée")
        self.assertEqual(list(self.dossier.glob("*.xlsx")), [])

    def test_refuse_un_televersement_vide_ou_corrompu(self):
        with self.assertRaisesRegex(ValueError, "vide"):
            analyser_televersement_excel("societes.xlsx", b"")
        with self.assertRaisesRegex(ValueError, "corrompu"):
            analyser_televersement_excel("societes.xlsx", b"pas un classeur")
        with self.assertRaisesRegex(ValueError, r"\.xlsx"):
            analyser_televersement_excel("societes.csv", b"contenu")

    def test_importe_ajoute_met_a_jour_et_restaure(self):
        ajouter_societe_surveillee(
            "542051180", commentaire="Ancien", chemin=self.base
        )
        supprimer_societe_surveillee("542051180", chemin=self.base)
        self._creer_classeur([
            ["542051180", "Non", "Restaurée"],
            ["552032534", "Oui", "Nouvelle"],
            ["123", "Oui", "Invalide"],
        ])
        apercu = analyser_fichier_excel(self.fichier)

        bilan = importer_apercu(apercu, self.base)

        self.assertEqual((bilan.ajouts, bilan.mises_a_jour), (1, 1))
        self.assertEqual(bilan.lignes_ignorees, 1)
        restauree = lire_societe_surveillee("542051180", self.base)
        self.assertFalse(restauree.actif)
        self.assertEqual(restauree.commentaire, "Restaurée")
        self.assertIsNone(restauree.date_archivage)
        self.assertTrue(lire_societe_surveillee("552032534", self.base).actif)

    def test_import_direct_et_lecteur_historique(self):
        self._creer_classeur([["542051180", "Oui", "Énergie"]])

        self.assertEqual(
            lire_sirens(self.fichier),
            [{
                "siren": "542051180",
                "actif": True,
                "commentaire": "Énergie",
            }],
        )
        bilan = importer_fichier_excel(self.fichier, self.base)

        self.assertEqual((bilan.ajouts, bilan.mises_a_jour), (1, 0))
        self.assertEqual(bilan.lignes_ignorees, 0)
        self.assertEqual(bilan.erreurs, ())

    def test_lecteur_historique_refuse_un_fichier_invalide(self):
        self._creer_classeur([["123", "Oui", "Invalide"]])

        with self.assertRaisesRegex(ValueError, "ligne 2"):
            lire_sirens(self.fichier)


if __name__ == "__main__":
    unittest.main()
