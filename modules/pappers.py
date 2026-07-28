from playwright.sync_api import Page, sync_playwright

from modules.modele import Societe


def lire_nom(page: Page) -> str:
    """
    Récupère la raison sociale de la société.
    """
    return page.locator("h1.big-text").inner_text().strip()


def lire_champ(page: Page, libelle: str) -> str:
    """
    Recherche un champ dans le tableau d'informations de Pappers.

    Exemple :
        Forme juridique
        Capital social
        Adresse
    """

    try:
        ligne = page.locator(f"tr:has(th:text-is('{libelle} :'))")
        return ligne.locator("td").inner_text().strip()

    except Exception:
        return ""


def lire_dirigeants(page: Page) -> str:
    """
    Récupère les dirigeants et leurs fonctions.
    """
    dirigeants = []
    lignes = page.locator("#representants-container li.dirigeant")

    for index in range(lignes.count()):
        ligne = lignes.nth(index)
        nom = ligne.locator(".nom").inner_text().strip()
        fonction = ligne.locator(".qualite").inner_text().strip()

        if nom and fonction:
            dirigeants.append(f"{nom} ({fonction})")
        elif nom:
            dirigeants.append(nom)

    return " ; ".join(dirigeants)


def lire_pappers(siren: str) -> Societe:
    """
    Lit les informations disponibles sur Pappers
    et retourne un objet Societe.
    """

    url = f"https://www.pappers.fr/entreprise/{siren}"

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(headless=False)

        page = browser.new_page()

        print(f"\nOuverture de : {url}")

        page.goto(url)

        page.wait_for_load_state("networkidle")

        societe = Societe(
            siren=siren,
            raison_sociale=lire_nom(page),
            forme_juridique=lire_champ(page, "Forme juridique"),
            capital=lire_champ(page, "Capital social"),
            adresse=lire_champ(page, "Adresse"),
            dirigeant=lire_dirigeants(page),
            source="Pappers",
        )

        browser.close()

        return societe
