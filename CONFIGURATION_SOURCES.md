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

L'API du Registre national des entreprises demande un compte INPI. Pour
enregistrer les identifiants dans un fichier chiffré par Windows DPAPI :

```powershell
python -m modules.secrets_windows
```

L'adresse e-mail et le mot de passe sont demandés de manière interactive. Le
mot de passe n'est pas affiché. Le coffre est lié au compte Windows courant et
stocké hors du dépôt dans :

```text
%LOCALAPPDATA%\Veille-SIREN\secrets\inpi-credentials.bin
```

Les variables d'environnement restent disponibles en remplacement :

```powershell
$env:VEILLE_SIREN_INPI_USER = "votre-adresse-email"
$env:VEILLE_SIREN_INPI_PASSWORD = "votre-mot-de-passe"
python main.py --source inpi
```

Les secrets ne doivent jamais être ajoutés à un fichier suivi par Git.

## Notion

La publication des rapports utilise un jeton d'intégration Notion. Après avoir
créé une intégration interne et lui avoir donné accès aux bases « Journal de
travail » et « Veille-SIREN — Rapports de veille », protéger le jeton avec :

```powershell
python -m modules.secrets_windows notion
```

Le jeton est demandé sans être affiché, chiffré avec Windows DPAPI et conservé
hors du dépôt dans :

```text
%LOCALAPPDATA%\Veille-SIREN\secrets\notion-token.bin
```

Après chaque rapport quotidien, l'application crée une entrée dans la base de
veille avec la date, les volumes, le nombre de modifications et les erreurs.
Le registre SQLite empêche une seconde publication du même fichier. Une panne
Notion est journalisée mais ne bloque ni la collecte ni le rapport local.

## Documentation officielle

- INSEE : https://portail-api.insee.fr/catalog/api/2ba0e549-5587-3ef1-9082-99cd865de66f
- INPI : https://www.inpi.fr/ressources/formalites-dentreprises/acces-lapi-formalite-rne
- BODACC : https://www.data.gouv.fr/dataservices/api-bulletin-officiel-des-annonces-civiles-et-commerciales-bodacc
- Notion : https://developers.notion.com/docs/getting-started
