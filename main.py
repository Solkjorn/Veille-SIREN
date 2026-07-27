from modules.initialisation import creer_dossiers
from modules.lecture_excel import lire_sirens
from modules.validation import siren_valide
from modules.pappers import tester_pappers

print("=" * 40)
print(" VEILLE JURIDIQUE DES SOCIÉTÉS")
print("=" * 40)
print()

creer_dossiers()

print()
print("Lecture du fichier Excel...")

from config import FICHIER_SIRENS

societes = lire_sirens(FICHIER_SIRENS)

print(f"{len(societes)} société(s) trouvée(s).")
print()

for societe in societes:

    if siren_valide(societe["siren"]):
        etat = "✅"
    else:
        etat = "❌"

    print(
        f"{etat} {societe['siren']} | "
        f"Actif : {societe['actif']} | "
        f"Commentaire : {societe['commentaire']}"
    )
    print()
print("Test de Playwright...")
print()

societe = tester_pappers(societes[0]["siren"])
print()
print("===== RÉSULTAT =====")
print(f"SIREN : {societe.siren}")
print(f"Nom : {societe.raison_sociale}")