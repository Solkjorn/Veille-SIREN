from playwright.sync_api import Page, sync_playwright

from modules.modele import Societe


DELAI_NAVIGATION_MS = 30_000


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


def lire_statut(page: Page) -> str:
    """
    Récupère le statut synthétique affiché par Pappers dans l'en-tête.

    Ce statut correspond à l'état juridique visible de l'entreprise
    (par exemple « Active » ou « Radiée »), qui peut différer du statut INSEE.
    """
    try:
        return page.locator("span.status").inner_text().strip()

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


def lire_derniere_publication_bodacc(page: Page) -> str:
    """
    Récupère la date de la publication BODACC la plus récente.

    Pappers présente les publications de la plus récente à la plus ancienne.
    """
    publications = page.locator(
        "div[tabname='Annonces BODACC'] li.publication"
    )

    if publications.count() == 0:
        return ""

    try:
        return (
            publications.nth(0)
            .locator("span.date")
            .inner_text()
            .strip()
        )

    except Exception:
        return ""


def lire_dernier_changement(page: Page) -> str:
    """
    Résume le changement décrit par la publication BODACC la plus récente.

    Lorsque l'annonce ne contient pas de description, son type reste utilisé
    afin de conserver une information exploitable.
    """
    publications = page.locator(
        "div[tabname='Annonces BODACC'] li.publication"
    )

    if publications.count() == 0:
        return ""

    publication = publications.nth(0)

    try:
        type_annonce = (
            publication.locator("span.type")
            .inner_text()
            .strip()
        )

    except Exception:
        type_annonce = ""

    try:
        description = (
            publication.locator(
                "div.annonce-contenu "
                "div:has(span:text-is('Description :'))"
            )
            .inner_text()
            .replace("Description :", "", 1)
            .strip()
        )

    except Exception:
        description = ""

    if type_annonce and description:
        return f"{type_annonce} — {description}"

    return type_annonce or description


def lire_pappers(siren: str) -> Societe:
    """
    Lit les informations disponibles sur Pappers
    et retourne un objet Societe.
    """

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)

        try:
            page = browser.new_page()
            return lire_pappers_avec_page(siren, page)

        finally:
            browser.close()


def lire_pappers_avec_page(siren: str, page: Page) -> Societe:
    """Collecte une société avec une page fournie par le moteur de collecte."""
    url = f"https://www.pappers.fr/entreprise/{siren}"
    print(f"\nOuverture de : {url}")
    page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=DELAI_NAVIGATION_MS,
    )
    page.locator("h1.big-text").wait_for(
        state="visible",
        timeout=DELAI_NAVIGATION_MS,
    )

    return Societe(
        siren=siren,
        raison_sociale=lire_nom(page),
        forme_juridique=lire_champ(page, "Forme juridique"),
        capital=lire_champ(page, "Capital social"),
        statut=lire_statut(page),
        adresse=lire_champ(page, "Adresse"),
        dirigeant=lire_dirigeants(page),
        derniere_publication_bodacc=lire_derniere_publication_bodacc(page),
        dernier_changement=lire_dernier_changement(page),
        source="Pappers",
    )
