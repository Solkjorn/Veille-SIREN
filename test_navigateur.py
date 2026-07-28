from modules.navigateur import Navigateur

nav = Navigateur()

nav.ouvrir()

page = nav.nouvelle_page()

page.goto("https://www.google.fr")

input("Appuie sur Entrée...")

nav.fermer()