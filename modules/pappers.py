from playwright.sync_api import sync_playwright
from modules.modele import Societe


def tester_pappers(siren: str):
    """
    Ouvre la fiche Pappers d'un SIREN
    et affiche le titre de la page.
    """

    url = f"https://www.pappers.fr/entreprise/{siren}"

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)

        page = browser.new_page()

        print(f"Ouverture de : {url}")

        page.goto(url)

        page.wait_for_load_state("networkidle")
        nom = page.locator("h1.big-text").inner_text()

        societe = Societe(
        siren=siren,
        raison_sociale=nom
        )


        print("\nLe navigateur reste ouvert.")
        input("Appuie sur Entrée lorsque tu as terminé...")

          
        browser.close()

        return societe