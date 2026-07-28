from playwright.sync_api import sync_playwright
from modules.modele import Societe


def lire_pappers(siren: str) -> Societe:
    """
    Ouvre la fiche Pappers correspondant au SIREN,
    récupère la raison sociale et retourne un objet Societe.
    """

    url = f"https://www.pappers.fr/entreprise/{siren}"

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        print(f"Ouverture de : {url}")

        page.goto(url)
        page.wait_for_load_state("networkidle")

        nom = page.locator("h1.big-text").inner_text().strip()

        societe = Societe(
            siren=siren,
            raison_sociale=nom,
            source="Pappers",
        )

        browser.close()

        return societe