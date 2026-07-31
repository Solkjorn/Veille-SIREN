from playwright.sync_api import sync_playwright


class Navigateur:

    def __init__(self, sans_interface: bool = False):
        self.sans_interface = sans_interface
        self.playwright = None
        self.browser = None

    def ouvrir(self):
        if self.browser:
            return self
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.sans_interface
        )
        return self

    def nouvelle_page(self):
        if not self.browser:
            raise RuntimeError("Le navigateur doit être ouvert avant usage.")
        return self.browser.new_page()

    def fermer(self):
        if self.browser:
            self.browser.close()
            self.browser = None

        if self.playwright:
            self.playwright.stop()
            self.playwright = None

    def __enter__(self):
        return self.ouvrir()

    def __exit__(self, type_erreur, erreur, trace):
        self.fermer()
