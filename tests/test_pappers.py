import unittest
from unittest.mock import MagicMock, patch

from modules.pappers import (
    DELAI_NAVIGATION_MS,
    lire_champ,
    lire_dernier_changement,
    lire_derniere_publication_bodacc,
    lire_pappers,
    lire_statut,
)


class TestLectureStatutPappers(unittest.TestCase):

    def test_lire_champ_retourne_la_valeur_nettoyee(self):
        page = MagicMock()
        ligne = page.locator.return_value
        ligne.locator.return_value.inner_text.return_value = "  ACTIF \n"

        resultat = lire_champ(page, "Statut INSEE")

        self.assertEqual(resultat, "ACTIF")
        page.locator.assert_called_once_with(
            "tr:has(th:text-is('Statut INSEE :'))"
        )
        ligne.locator.assert_called_once_with("td")

    def test_lire_champ_retourne_une_chaine_vide_si_absent(self):
        page = MagicMock()
        page.locator.side_effect = RuntimeError("champ absent")

        self.assertEqual(lire_champ(page, "Statut INSEE"), "")

    def test_lire_statut_retourne_le_statut_synthetique(self):
        page = MagicMock()
        page.locator.return_value.inner_text.return_value = "  Radiée \n"

        self.assertEqual(lire_statut(page), "Radiée")
        page.locator.assert_called_once_with("span.status")

    def test_lire_statut_retourne_une_chaine_vide_si_absent(self):
        page = MagicMock()
        page.locator.side_effect = RuntimeError("statut absent")

        self.assertEqual(lire_statut(page), "")

    def test_lire_derniere_publication_bodacc_retourne_la_date(self):
        page = MagicMock()
        publications = page.locator.return_value
        publications.count.return_value = 2
        publication = publications.nth.return_value
        publication.locator.return_value.inner_text.return_value = (
            "  10/07/2026 \n"
        )

        resultat = lire_derniere_publication_bodacc(page)

        self.assertEqual(resultat, "10/07/2026")
        page.locator.assert_called_once_with(
            "div[tabname='Annonces BODACC'] li.publication"
        )
        publications.nth.assert_called_once_with(0)
        publication.locator.assert_called_once_with("span.date")

    def test_lire_derniere_publication_bodacc_gere_l_absence(self):
        page = MagicMock()
        page.locator.return_value.count.return_value = 0

        self.assertEqual(lire_derniere_publication_bodacc(page), "")

    def test_lire_dernier_changement_retourne_type_et_description(self):
        page = MagicMock()
        publications = page.locator.return_value
        publications.count.return_value = 1
        publication = publications.nth.return_value

        type_annonce = MagicMock()
        type_annonce.inner_text.return_value = " MODIFICATION "
        description = MagicMock()
        description.inner_text.return_value = (
            "Description : Modification survenue sur le capital."
        )
        publication.locator.side_effect = [type_annonce, description]

        resultat = lire_dernier_changement(page)

        self.assertEqual(
            resultat,
            "MODIFICATION — Modification survenue sur le capital.",
        )

    def test_lire_dernier_changement_conserve_le_type_sans_description(self):
        page = MagicMock()
        publications = page.locator.return_value
        publications.count.return_value = 1
        publication = publications.nth.return_value

        type_annonce = MagicMock()
        type_annonce.inner_text.return_value = "DÉPÔT DES COMPTES"
        publication.locator.side_effect = [
            type_annonce,
            RuntimeError("description absente"),
        ]

        self.assertEqual(
            lire_dernier_changement(page),
            "DÉPÔT DES COMPTES",
        )

    def test_lire_dernier_changement_gere_l_absence_d_annonce(self):
        page = MagicMock()
        page.locator.return_value.count.return_value = 0

        self.assertEqual(lire_dernier_changement(page), "")

    @patch(
        "modules.pappers.lire_dernier_changement",
        return_value="MODIFICATION — Changement de capital.",
    )
    @patch(
        "modules.pappers.lire_derniere_publication_bodacc",
        return_value="10/07/2026",
    )
    @patch("modules.pappers.lire_dirigeants", return_value="Jane Doe (Gérante)")
    @patch("modules.pappers.lire_statut", return_value="ACTIF")
    @patch("modules.pappers.lire_champ")
    @patch("modules.pappers.lire_nom", return_value="SOCIÉTÉ TEST")
    @patch("modules.pappers.sync_playwright")
    def test_lire_pappers_alimente_le_statut_de_la_societe(
        self,
        mock_sync_playwright,
        mock_lire_nom,
        mock_lire_champ,
        mock_lire_statut,
        mock_lire_dirigeants,
        mock_lire_derniere_publication_bodacc,
        mock_lire_dernier_changement,
    ):
        playwright = (
            mock_sync_playwright.return_value.__enter__.return_value
        )
        browser = playwright.chromium.launch.return_value
        page = browser.new_page.return_value
        mock_lire_champ.side_effect = [
            "SARL",
            "10 000 €",
            "1 RUE DU TEST, 75000 PARIS",
        ]

        societe = lire_pappers("123456789")

        self.assertEqual(societe.statut, "ACTIF")
        self.assertEqual(
            societe.derniere_publication_bodacc,
            "10/07/2026",
        )
        self.assertEqual(
            societe.dernier_changement,
            "MODIFICATION — Changement de capital.",
        )
        self.assertEqual(societe.siren, "123456789")
        self.assertEqual(societe.source, "Pappers")
        mock_lire_statut.assert_called_once_with(page)
        mock_lire_derniere_publication_bodacc.assert_called_once_with(page)
        mock_lire_dernier_changement.assert_called_once_with(page)
        page.goto.assert_called_once_with(
            "https://www.pappers.fr/entreprise/123456789",
            wait_until="domcontentloaded",
            timeout=DELAI_NAVIGATION_MS,
        )
        page.locator.assert_any_call("h1.big-text")
        browser.close.assert_called_once_with()

    @patch("modules.pappers.sync_playwright")
    def test_lire_pappers_ferme_le_navigateur_apres_une_erreur(
        self,
        mock_sync_playwright,
    ):
        playwright = (
            mock_sync_playwright.return_value.__enter__.return_value
        )
        browser = playwright.chromium.launch.return_value
        page = browser.new_page.return_value
        page.goto.side_effect = RuntimeError("navigation impossible")

        with self.assertRaisesRegex(
            RuntimeError,
            "navigation impossible",
        ):
            lire_pappers("123456789")

        browser.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
