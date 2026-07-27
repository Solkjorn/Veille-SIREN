from modules.initialisation import creer_dossiers
from modules.lecture_excel import lire_sirens

print("=" * 40)
print(" VEILLE JURIDIQUE DES SOCIÉTÉS")
print("=" * 40)
print()

creer_dossiers()

print()
print("Lecture du fichier Excel...")

societes = lire_sirens("sirens.xlsx")

print(f"{len(societes)} société(s) trouvée(s).")
print()

for societe in societes:
    print(
        f"SIREN : {societe['siren']} | "
        f"Actif : {societe['actif']} | "
        f"Commentaire : {societe['commentaire']}"
    )