from config import FICHIER_SIRENS
from modules.collecteur import collecter_societe
from modules.initialisation import creer_dossiers
from modules.lecture_excel import lire_sirens
from modules.validation import siren_valide


print("=" * 40)
print(" VEILLE JURIDIQUE DES SOCIÉTÉS")
print("=" * 40)
print()

creer_dossiers()

print()
print("Lecture du fichier Excel...")

societes = lire_sirens(FICHIER_SIRENS)

print(f"{len(societes)} société(s) trouvée(s).")
print()

for societe_excel in societes:
    siren = societe_excel["siren"]

    if siren_valide(siren):
        etat = "✅"
    else:
        etat = "❌"

    print(
        f"{etat} {siren} | "
        f"Actif : {societe_excel['actif']} | "
        f"Commentaire : {societe_excel['commentaire']}"
    )
    print()


if societes:
    premier_siren = societes[0]["siren"]

    print("Test de Playwright...")
    print(f"Lecture de la société portant le SIREN {premier_siren}...")
    print()

    societe_collectee = collecter_societe(premier_siren)

    print()
    print("===== RÉSULTAT =====")
    print(f"SIREN           : {societe_collectee.siren}")
    print(f"Nom             : {societe_collectee.raison_sociale}")
    print(f"Forme juridique : {societe_collectee.forme_juridique}")
    print(f"Capital         : {societe_collectee.capital}")
    print(f"Adresse         : {societe_collectee.adresse}")
    print(f"Source          : {societe_collectee.source}")

else:
    print("Aucune société n’a été trouvée dans le fichier Excel.")