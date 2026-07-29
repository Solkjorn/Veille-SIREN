from playwright.sync_api import sync_playwright


class Navigateur:

    def __init__(self):
        self.playwright = None
        self.browser = None

    def ouvrir(self):

        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=False
        )

    def nouvelle_page(self):

        return self.browser.new_page()

    def fermer(self):

        if self.browser:
            self.browser.close()

        if self.playwright:
            self.playwright.stop()