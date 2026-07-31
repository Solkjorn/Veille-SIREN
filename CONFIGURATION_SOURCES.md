# Configuration des sources de collecte

La source se sélectionne avec l'option `--source` :

```powershell
python main.py --source pappers
python main.py --source bodacc
python main.py --source insee
python main.py --source inpi
```

Le mode sans fenêtre Chromium reste disponible pour Pappers :

```powershell
python main.py --source pappers --sans-interface
```

## BODACC

L'API BODACC est ouverte et ne demande aucun identifiant.

## INSEE

L'API Sirene demande une clé d'intégration. Par défaut, Veille-SIREN la lit
dans un fichier chiffré par Windows DPAPI, lié au compte Windows courant et
stocké hors du dépôt dans :

```text
%LOCALAPPDATA%\Veille-SIREN\secrets\insee-api-key.bin
```

La variable d'environnement reste disponible comme solution de remplacement :

```powershell
$env:VEILLE_SIREN_INSEE_API_KEY = "votre-cle"
python main.py --source insee
```

## INPI

L'API du Registre national des entreprises demande un compte INPI. Les
identifiants sont lus depuis l'environnement :

```powershell
$env:VEILLE_SIREN_INPI_USER = "votre-adresse-email"
$env:VEILLE_SIREN_INPI_PASSWORD = "votre-mot-de-passe"
python main.py --source inpi
```

Les secrets ne doivent jamais être ajoutés à un fichier suivi par Git.

## Documentation officielle

- INSEE : https://portail-api.insee.fr/catalog/api/2ba0e549-5587-3ef1-9082-99cd865de66f
- INPI : https://www.inpi.fr/ressources/formalites-dentreprises/acces-lapi-formalite-rne
- BODACC : https://www.data.gouv.fr/dataservices/api-bulletin-officiel-des-annonces-civiles-et-commerciales-bodacc
