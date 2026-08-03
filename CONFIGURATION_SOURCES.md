# Configuration des sources de collecte

La source se sélectionne avec l'option `--source` :

```powershell
python main.py --source multisource
python main.py --source annuaire
python main.py --source bodacc
python main.py --source insee
python main.py --source inpi
```

Sans option, `multisource` est utilisé. Ce mode réunit l'Annuaire des
entreprises, l'INSEE, l'INPI et le BODACC sans ouvrir de navigateur.

## Annuaire des entreprises

L'API Recherche d'entreprises est officielle, gratuite et sans clé. Elle
alimente notamment l'identité, l'état administratif, l'adresse du siège et les
dirigeants. Veille-SIREN envoie un `User-Agent` explicite et applique ses
reprises progressives aux réponses temporaires, notamment HTTP 429.

## Pappers — secours manuel uniquement

Pappers n'est plus utilisé par la collecte automatique. Son connecteur est
conservé provisoirement pour un contrôle manuel ponctuel :

```powershell
python main.py --source pappers --sans-interface
```

Cette commande ouvre Chromium et reste sensiblement plus lente que les API
officielles. Elle ne doit pas servir à une extraction automatisée récurrente.

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

Pour publier le compte rendu de développement complet à la clôture d'une
session :

```powershell
python -m modules.notion --rapport-developpement rapports/developpement_YYYYMMDD.md
```

Le fichier doit suivre exactement ce nom. Les titres, listes et paragraphes
Markdown sont convertis en blocs Notion, puis la publication est inscrite dans
le même registre anti-doublon.

## Documentation officielle

- Annuaire des entreprises : https://recherche-entreprises.api.gouv.fr/docs/
- INSEE : https://portail-api.insee.fr/catalog/api/2ba0e549-5587-3ef1-9082-99cd865de66f
- INPI : https://www.inpi.fr/ressources/formalites-dentreprises/acces-lapi-formalite-rne
- BODACC : https://www.data.gouv.fr/dataservices/api-bulletin-officiel-des-annonces-civiles-et-commerciales-bodacc
- Notion : https://developers.notion.com/docs/getting-started

## Planification Windows

La tâche `Veille-SIREN - collecte hebdomadaire` exécute la collecte chaque
lundi à 7 h, puis génère la synthèse après la fin de la collecte. Si le PC est
éteint à 7 h, Windows lance la tâche dès que possible au prochain démarrage.
Une seconde exécution est ignorée tant que la première n'est pas terminée.

Pour créer ou remettre à jour cette tâche :

```powershell
python -m modules.planification --installer --source multisource
```

Le jour, l'heure, la minute et la source peuvent également être modifiés depuis
la page « Automatisation » de l'interface web.

La tâche utilise l'environnement Python local hors du dépôt. Le mode
multisource officiel n'ouvre pas Chromium. Elle est limitée à deux heures et
ne s'exécute que lorsque le compte Windows de l'utilisateur est ouvert.

## Envoi SMTP

La synthèse peut être envoyée par tout fournisseur SMTP compatible avec TLS.
Les paramètres et le mot de passe sont chiffrés par Windows DPAPI hors du
dépôt. Pour les enregistrer :

```powershell
python -m modules.secrets_windows smtp
```

Le serveur, le port, l'identifiant, le mot de passe d'application, l'adresse
d'expédition et le destinataire sont demandés de manière interactive. Une
absence de configuration ou un échec SMTP est journalisé sans interrompre la
publication locale et Notion.
