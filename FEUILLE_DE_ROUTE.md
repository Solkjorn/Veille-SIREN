# Feuille de route de Veille-SIREN

## Vision du produit

Veille-SIREN doit devenir une application web de veille juridique permettant
de :

- gérer une liste de sociétés surveillées par leur SIREN ;
- ajouter, modifier, activer, désactiver ou supprimer une société ;
- importer des listes de SIREN depuis des fichiers Excel ;
- contrôler les SIREN, les doublons et les lignes incorrectes ;
- collecter périodiquement les informations juridiques ;
- conserver l'historique des collectes ;
- détecter et présenter les changements ;
- produire des rapports de veille en HTML ;
- envoyer automatiquement un rapport hebdomadaire de veille par e-mail ;
- publier les rapports de veille dans Notion ;
- produire des rapports journaliers de développement séparés ;
- fonctionner à terme depuis une interface web.

Pappers est la première source de collecte. L'architecture doit permettre
l'ajout ultérieur de sources officielles telles que l'INSEE, l'INPI et le
BODACC.

## Règle de pilotage

Cette feuille de route constitue le plan de référence du projet.

Une phase peut être précisée en cours de réalisation, mais toute modification
importante de périmètre, suppression de phase ou inversion de l'ordre des
phases doit être discutée avec le propriétaire du projet avant sa mise en
œuvre.

## État actuel

Le socle technique disponible comprend :

- la lecture d'une liste de sociétés depuis Excel ;
- la validation des SIREN ;
- la collecte des sociétés actives ;
- l'extraction des principales données Pappers ;
- la collecte de la dernière publication et du dernier changement BODACC ;
- la gestion des erreurs société par société ;
- la journalisation avec rotation automatique ;
- la conservation des instantanés dans SQLite ;
- la comparaison entre deux collectes ;
- la détection et l'affichage des changements ;
- la génération de rapports Markdown ;
- une suite de plus de 50 tests automatisés ;
- un dépôt de travail local dans `D:\Documents\Projets\Veille-SIREN`,
  synchronisé avec GitHub ;
- un environnement Python local séparé du dépôt.

## Phase 1 — Modèle des sociétés surveillées

Objectif : faire de SQLite la source centrale de l'application.

- Ajouter une table `societes_surveillees`.
- Stocker le SIREN, l'état actif, le commentaire et les dates techniques.
- Créer les services d'ajout, de lecture, de modification et de suppression.
- Fournir des opérations explicites d'activation, de désactivation et de
  restauration après archivage.
- Définir la stratégie de suppression ou d'archivage.
- Empêcher les doublons.
- Utiliser cette table comme source des collectes.

État : terminée. Stratégie retenue : archivage logique avec restauration.

## Phase 2 — Import Excel complet

- Téléverser et analyser un fichier `.xlsx`.
- Vérifier la feuille et les colonnes attendues.
- Normaliser et valider les SIREN.
- Détecter les doublons.
- Prévisualiser les données avant import.
- Réaliser un import transactionnel.
- Produire un bilan des ajouts, mises à jour, lignes ignorées et erreurs.

État : terminée pour le service backend. L'analyse, la prévisualisation,
l'import transactionnel et la réception en mémoire d'un fichier téléversé
sont disponibles. Leur raccordement à l'interface est prévu en phase 3.

## Phase 3 — Interface web minimale

- Créer un tableau de bord.
- Afficher la liste des sociétés surveillées.
- Afficher une colonne « Dernière modification » contenant la date de la
  dernière publication BODACC.
- Afficher une colonne « Dernière collecte » contenant la date et l'heure du
  dernier instantané enregistré, distincte de la modification de la fiche de
  surveillance.
- Afficher un mini-rapport dépliable en cliquant sur le SIREN ou le nom d'une
  société ; conserver dans ce rapport le détail textuel du dernier changement
  et afficher son objet en gras pour le rendre facilement repérable.
- Ajouter et modifier une société.
- Activer ou désactiver une société.
- Supprimer ou archiver une société avec confirmation.
- Importer un fichier Excel.
- Isoler l'import Excel dans une page « Imports » de la navigation, sans
  bandeau d'import sur le tableau de bord.
- Consulter l'historique d'une société.
- Consulter les collectes, erreurs et rapports.

État : terminée. Socle Flask retenu. Le tableau de bord et la liste des
sociétés surveillées sont disponibles. L'ajout, la modification du
commentaire, l'activation, la désactivation, l'archivage et la restauration
sont accessibles depuis le tableau de bord. L'import Excel dispose d'une
prévisualisation et d'une confirmation explicite avant écriture. L'historique
des collectes et les changements entre deux instantanés sont consultables par
société. Les collectes récentes, le journal d'exécution et les rapports sont
consultables depuis la navigation principale. Le tableau de bord affiche la
date et l'heure de la dernière collecte réussie pour chaque société.
L'archivage demande une confirmation visible. L'ensemble du périmètre prévu
pour cette phase est couvert par les tests automatisés et a fait l'objet d'un
contrôle visuel local.

## Phase 4 — Moteur de collecte

- Séparer complètement le moteur de collecte de l'interface.
- Réutiliser un navigateur pour plusieurs sociétés.
- Prévoir un mode visible et un mode sans interface.
- Enregistrer l'état des tâches.
- Ajouter des tentatives en cas d'erreur temporaire.
- Empêcher les collectes simultanées d'un même SIREN.
- Préparer l'ajout d'autres sources.

État : terminée. Une même session Chromium est désormais réutilisée pour
plusieurs sociétés, avec une page isolée et systématiquement fermée par SIREN.
Les modes visible et sans interface sont disponibles. Le cycle de vie des
tâches est enregistré dans SQLite, les erreurs temporaires déclenchent une
nouvelle tentative limitée et un verrou empêche deux collectes simultanées du
même SIREN. Le moteur dépend maintenant d'un contrat de source indépendant ;
Pappers en est la première implémentation et d'autres sources pourront être
ajoutées sans modifier son cycle d'exécution. Les adaptateurs INSEE, INPI et
BODACC sont maintenant disponibles. BODACC fonctionne sans identifiant.
L'application « Veille SIREN » est créée sur le portail INSEE, sa souscription
à API Sirene 3.11 est active et la collecte réelle a été validée. Sa clé est
chiffrée avec Windows DPAPI, liée au compte Windows courant et conservée hors
du dépôt ; une variable d'environnement reste possible en remplacement.
L'accès « Informations des entreprises » des APIs RNE a été activé pour
INPI. Les identifiants sont protégés par Windows DPAPI hors du dépôt et la
structure JSON réelle a été intégrée. L'authentification et une collecte réelle
par SIREN ont été validées. La phase 5 peut maintenant commencer.

## Phase 5 — Rapports HTML

- Faire du HTML le format principal des rapports de veille.
- Créer une synthèse hebdomadaire adaptée à l'envoi par e-mail.
- Ajouter un résumé général de l'exécution.
- Séparer les sociétés modifiées de celles sans changement.
- Afficher les anciennes et nouvelles valeurs.
- Ajouter les dates, sources et états de collecte.
- Permettre la consultation depuis l'interface web.
- Définir une politique de conservation.

Le Markdown peut rester disponible comme format secondaire.

État : terminée. Le rapport HTML autonome est devenu le format principal de
chaque exécution et le Markdown est généré en parallèle comme format secondaire.
Le rapport contient un résumé des réussites, modifications, sociétés stables
et erreurs ; il sépare les sociétés modifiées de celles sans changement,
affiche les valeurs avant/après, les données collectées, la date, la source et
l'état. Les rapports HTML et Markdown sont consultables et téléchargeables
depuis l'interface web. La synthèse hebdomadaire est disponible : elle utilise
une fenêtre glissante de sept jours, compare le
dernier état de la période à l'état antérieur, inclut les échecs enregistrés
dans SQLite et produit un HTML distinct adapté à l'e-mail. Elle peut être
générée avec `python main.py --synthese-hebdomadaire`. La politique retenue
conserve les rapports de veille et synthèses pendant 365 jours, puis supprime
automatiquement uniquement les fichiers générés reconnus. Les rapports de
développement sont conservés sans limite et les fichiers inconnus sont exclus
du nettoyage.

## Phase 6 — Rapports journaliers de développement

Créer des rapports distincts des rapports de veille contenant :

- la date ;
- l'heure de début et l'heure de fin de chaque session ;
- le temps passé ;
- les travaux réalisés ;
- les modules concernés ;
- les tests exécutés ;
- les difficultés et décisions ;
- le commit Git associé ;
- la prochaine étape.

État : terminée. Tous les rapports de développement suivent maintenant une
structure commune couvrant les horaires de session, le temps, les travaux, les
modules, les tests, les difficultés et décisions, le commit et la prochaine
étape. Un test automatique contrôle cette structure pour chaque rapport.

## Phase 7 — Intégration Notion — TERMINÉE

- Définir les bases ou pages Notion cibles.
- Publier les rapports quotidiens de veille.
- Publier les rapports journaliers de développement.
- Configurer l'authentification de l'application.
- Conserver les identifiants Notion utiles dans SQLite.
- Empêcher les publications en double.
- Gérer les erreurs Notion sans bloquer la collecte.

État : terminé. La connexion au workspace Notion personnel est
opérationnelle. La base existante « Journal de travail » reste la cible des
comptes rendus de développement. Une base distincte « Veille-SIREN — Rapports
de veille » a été créée pour les rapports juridiques quotidiens et
hebdomadaires, avec les champs de date, type, statut, identifiant stable,
volumes, modifications, erreurs et fichier source. Les identifiants non
sensibles des deux sources de données sont conservés dans SQLite. Un registre
local des publications empêche les doublons. Le compte rendu du 1er août a été
publié dans « Journal de travail » et enregistré dans le registre local. Les
anciens modèles Notion « Journal », « Task List » et « Media » ont été placés
dans la corbeille afin de ne conserver que les deux structures du projet.
Le client HTTP de publication est désormais intégré : le jeton est conservé
hors du dépôt dans un coffre Windows DPAPI, les rapports quotidiens alimentent
la base de veille avec leurs métadonnées, l'anti-doublon est appliqué avant
l'appel réseau et les erreurs Notion sont journalisées sans interrompre la
collecte. Le jeton réel est maintenant chiffré, son authentification et l'accès
aux deux bases ont été validés. Un premier rapport quotidien réel, construit à
partir de quatre instantanés SQLite, a été publié avec succès ; son inscription
dans le registre anti-doublon a également été contrôlée. Les rapports de
développement disposent désormais d'une commande de publication dédiée : leur
Markdown est converti en blocs Notion et l'anti-doublon empêche une seconde
création. La phase 7 est terminée. La structure a été
volontairement simplifiée : le Journal ne conserve que le titre, la date et le
statut ; les deux vues portent des noms explicites, sont triées par date
décroissante et n'affichent que les champs utiles. Les métadonnées techniques
restent disponibles pour l'application mais sont masquées dans la vue.

## Phase 8 — Automatisation — TERMINÉE

État : terminé. La collecte est hebdomadaire, chaque lundi à 7 h, avec
rattrapage au prochain démarrage de Windows si l'ordinateur était éteint. La
synthèse est générée immédiatement après la fin de la collecte, jamais en
parallèle. La tâche Windows réelle est installée avec Pappers comme source,
le mode sans interface, une limite de deux heures et le refus des exécutions
simultanées. Sa première échéance est le 03/08/2026 à 7 h.
La synthèse est automatiquement publiée dans Notion avec ses volumes et son
statut. Une page « Automatisation » affiche l'état de la tâche, les dernières
et prochaines exécutions et permet un lancement manuel protégé par CSRF.
Le connecteur d'envoi SMTP avec TLS est intégré ; ses paramètres sont chiffrés
par DPAPI et ses erreurs ne bloquent pas la chaîne. Gmail est configuré comme
expéditeur gratuit et Proton Mail comme destinataire. Un premier envoi réel de
la synthèse HTML a été accepté avec succès par `smtp.gmail.com:587`.
Le tableau de bord sépare désormais les sociétés ayant eu au moins une
modification entre leurs deux dernières collectes de celles restées stables.
La page « Imports » propose un modèle Excel vide et conforme, avec la feuille
`Societes` et les colonnes `SIREN`, `Actif` et `Commentaire`.
Le jour, l'heure, la minute et la source sont configurables depuis la page
« Automatisation ». Chaque chaîne hebdomadaire dispose désormais d'une entrée
SQLite globale avec son statut, ses horaires, ses volumes, son rapport et son
éventuel message d'erreur. Les vingt dernières exécutions et leur bilan cumulé
sont affichés dans l'interface. Une simulation complète a été déclenchée le
02/08/2026 au moyen de la tâche Windows réelle, dans les mêmes conditions
qu'un lundi à 7 h. Les 56 sociétés actives ont été prises en compte en 27
minutes : 54 collectes ont réussi et deux ont été journalisées en erreur après
expiration du délai d'affichage Pappers. Le rapport et la synthèse HTML ont
été générés, leurs publications Notion ont réussi, l'envoi Gmail vers Proton
Mail a réussi et Windows a retourné le code `0`. L'historique SQLite contient
le bilan complet. La prochaine exécution reste planifiée le 03/08/2026 à 7 h.
Une reprise ciblée des sociétés en erreur et l'optimisation du temps de
collecte Pappers sont conservées comme améliorations futures.

- Planifier les collectes hebdomadaires le lundi à 7 h.
- Rendre l'heure configurable.
- Générer automatiquement le rapport hebdomadaire après la collecte.
- Envoyer le rapport hebdomadaire par e-mail aux destinataires configurés.
- Journaliser les succès et les échecs d'envoi sans bloquer les collectes.
- Permettre un lancement manuel depuis l'interface.
- Afficher les dernières et prochaines exécutions.
- Produire un bilan des succès, changements et erreurs.
- Publier automatiquement les rapports.
- Conserver l'historique des exécutions.

## Phase 9 — Déploiement et sécurisation — TERMINÉE

État : terminé. Le mode retenu est une application locale, gratuite,
mono-utilisateur et accessible uniquement depuis l'ordinateur du propriétaire.
SQLite est conservé. Une sauvegarde vérifiée est désormais créée après chaque
chaîne hebdomadaire et peut aussi être déclenchée avec `main.py --sauvegarder`.
Elle contient une copie cohérente de SQLite, les rapports et les secrets sous
leur forme DPAPI chiffrée, dans `%LOCALAPPDATA%\Veille-SIREN\sauvegardes`, avec
une rétention de douze archives. Une première archive réelle a été validée le
02/08/2026. Le lancement `python -m webapp` limite Flask à `127.0.0.1`, sans
mode debug, et l'application applique des en-têtes HTTP et cookies renforcés.
La dernière archive réelle a été restaurée dans un emplacement temporaire :
ses 26 fichiers sont lisibles, les sept tables SQLite sont présentes et le
contrôle d'intégrité retourne `ok`. La tâche Windows réelle autorise désormais
le réveil du PC et deux reprises espacées de cinq minutes en cas d'échec, tout
en conservant les privilèges minimaux, la limite de deux heures et le refus des
exécutions simultanées. La phase 9 est clôturée.

- Décider si l'application reste locale, fonctionne sur le réseau local ou
  est hébergée en ligne.
- Définir l'authentification et le nombre d'utilisateurs.
- Évaluer une éventuelle migration de SQLite vers PostgreSQL.
- Protéger les secrets et accès Notion.
- Organiser les sauvegardes.
- Sécuriser Playwright et la planification.

## Partie 2 — Évolutions fonctionnelles

La partie 2 commencera après la clôture de la phase 9. L'ensemble de son
périmètre a été validé le 02/08/2026. Les phases seront réalisées dans l'ordre
ci-dessous afin que les fonctions visibles reposent sur des données fiables.

### Phase 10 — Collecte multisource fiable — TERMINÉE

- Utiliser en priorité les sources officielles selon leur spécialité : INSEE
  pour l'identité et l'état administratif, INPI pour les données juridiques et
  BODACC pour les publications et modifications.
- Conserver Pappers comme complément ou solution de repli.
- Fusionner les réponses sans remplacer une information fiable par une valeur
  vide ou moins récente.
- Conserver la source et la date de chaque information collectée.
- Détecter et signaler les contradictions entre sources.
- Relancer automatiquement et uniquement les sociétés en erreur.
- Appliquer un délai progressif aux nouvelles tentatives.
- Afficher les résultats et erreurs de chaque source dans l'historique.
- Mesurer et réduire la durée globale de collecte.

Première tranche prévue : définir les règles de priorité champ par champ,
introduire un collecteur composite testé, puis valider les résultats sur un
petit groupe de SIREN avant de modifier la tâche hebdomadaire réelle.

État : première tranche réalisée. Un collecteur composite fusionne INSEE,
INPI, BODACC et Pappers selon des priorités explicites par champ. Il conserve
la provenance des valeurs, détecte les contradictions et tolère l'échec d'une
source tant qu'une autre fournit un résultat. La tâche hebdomadaire réelle
reste sur Pappers. Une validation sans écriture a réussi sur les SIREN
304154719, 917396103 et 922454111 avec les quatre sources disponibles et aucune
erreur de connecteur. Les règles ont ensuite été corrigées pour privilégier les
libellés juridiques lisibles, normaliser les dates équivalentes et enrichir les
dépôts de comptes BODACC sans considérer un résumé comme une contradiction.
Une contre-vérification réelle sur 922454111 a confirmé ces corrections.
La stratégie validée exécute désormais INSEE, INPI et BODACC en premier, puis
Pappers uniquement si un champ essentiel manque. Un complément Pappers complet
reste prévu lors de la première collecte hebdomadaire de chaque mois. Sur les
trois SIREN de contrôle, le mode officiel rapide est passé de 100 secondes à
3,8 secondes sans erreur. La provenance, les erreurs par source et les
contradictions disposent de colonnes JSON rétrocompatibles dans SQLite et sont
consultables dans l'historique web. La migration additive de la base réelle a
été appliquée sans modifier les collectes existantes.
L'API Entreprise Pappers a été écartée le 02/08/2026 : elle offre seulement
100 crédits initiaux sous condition d'adresse professionnelle, puis devient
payante à raison d'un crédit par fiche. Pappers reste donc utilisé uniquement
par navigation web conditionnelle afin de préserver un fonctionnement gratuit.
Une validation avec écriture et relecture dans une base isolée a réussi sur les
trois SIREN de contrôle en 4,09 secondes. La tâche Windows réelle utilise
désormais la source `multisource`. Les champs d'enrichissement absents d'une
collecte rapide conservent leur dernière valeur connue avec une provenance
`Historique`, afin de ne pas créer de fausse alerte de suppression.
Les reprises sont désormais appliquées uniquement à la source temporairement
défaillante, avec trois essais et des attentes progressives de 1 puis 2
secondes. Les erreurs permanentes, notamment les refus HTTP 401/403, ne sont
pas réessayées. Chaque provenance conserve également sa date de collecte ; une
valeur historique conserve la date de son dernier enrichissement. Ces données
sont enregistrées dans SQLite et affichées dans l'historique web. La phase 10
est terminée avec la tâche Windows réelle configurée en `multisource`.

### Phase 11 — Alertes enrichies — TERMINÉE

- Classer chaque changement selon trois niveaux : critique, important ou
  informatif.
- Traiter comme événements prioritaires la cessation, la radiation, les
  procédures collectives, les changements de dirigeant, les transferts de
  siège, les modifications de capital, les dépôts de comptes et les
  modifications d'activité.
- Permettre de choisir les catégories d'alertes suivies pour chaque société.
- Placer les événements critiques et importants en tête de l'interface, de la
  synthèse hebdomadaire et du courriel.
- Prévoir une alerte immédiate configurable pour les événements critiques,
  sans supprimer la synthèse hebdomadaire.
- Conserver la règle ayant déclenché l'alerte, sa source, sa date, son niveau
  et son état de lecture ou de traitement.
- Éviter les alertes en double lorsqu'un même événement provient de plusieurs
  sources.

Cette phase commencera après la phase 10 afin que la classification s'appuie
sur des données multisources consolidées et traçables. La première tranche
portera sur la taxonomie, les règles de classement et leur couverture par des
tests avant tout envoi immédiat réel.

État : première tranche réalisée. Chaque changement possède désormais un
niveau `critique`, `important` ou `informatif`, une catégorie et la règle de
classement appliquée. Les radiations, cessations et procédures collectives sont
critiques ; les dirigeants, sièges, capitaux, comptes, activités et formes
juridiques sont importants. Les alertes sont triées par priorité et ces
informations apparaissent dans les rapports HTML/Markdown et l'historique web.
L'envoi immédiat des nouvelles alertes critiques est disponible et reste
désactivé par défaut. Il peut être activé explicitement depuis la page web
« Alertes ». Seule une alerte effectivement ajoutée à SQLite déclenche le
courriel, ce qui exclut les événements anciens et les doublons ; une erreur
SMTP est journalisée sans interrompre la collecte.
Les alertes détectées sont maintenant persistées dans SQLite avec un
identifiant stable, leur source, leur date et un état `nouvelle`, `lue` ou
`traitee`. Un même événement reçu plusieurs fois le même jour est dédoublonné.
La page web « Alertes » les présente par priorité, permet de filtrer le niveau
et l'état, d'ouvrir l'historique de la société et de modifier leur état avec la
protection CSRF. La table a été créée dans la base réelle sans générer d'alerte
artificielle.
Les préférences sont désormais configurables depuis l'historique de chaque
société. Toutes les catégories sont actives par défaut ; une catégorie
désactivée bloque uniquement la création d'une nouvelle alerte, sans retirer le
changement des collectes, de l'historique ou des rapports. La table de
préférences a été créée dans la base réelle avec le comportement par défaut,
sans devoir écrire onze lignes pour chacune des 56 sociétés. La phase est
terminée : classification, préférences par société, priorité, traçabilité,
dédoublonnage, traitement et notification immédiate configurable sont couverts
par la suite automatisée.

### Phase 12 — Fiche société enrichie — TERMINÉE

- Réunir l'identité, les coordonnées, l'état administratif, les dirigeants,
  les annonces BODACC, les actes et comptes INPI et les commentaires internes.
- Présenter une chronologie des événements et des modifications.
- Afficher la provenance, la date et le résultat de la dernière vérification.
- Ajouter des liens directs vers les sources officielles.

État : première tranche réalisée. La page d'historique présente désormais une
fiche de situation fondée sur la dernière collecte : identité, SIREN, état
administratif, forme juridique, capital, dirigeants, siège, dernière
publication BODACC, sources et date de vérification. Des accès directs vers
l'Annuaire des entreprises, le RNE de l'INPI, l'avis Sirene de l'INSEE et le
BODACC sont proposés. La chronologie réunit maintenant les collectes, les
changements détectés et les alertes de la société, classés du plus récent au
plus ancien. Chaque alerte y conserve son niveau, son état, sa règle, sa source
et ses valeurs avant/après. La prochaine tranche intégrera les publications
disponibles avant d'étendre, si les API le permettent, les actes et comptes
INPI. La documentation officielle confirme que les comptes annuels sont
disponibles en JSON/PDF et les actes en PDF via des API distinctes de l'API RNE
déjà connectée. Leur intégration nécessitera donc un modèle documentaire dédié
et une collecte de métadonnées, sans télécharger automatiquement tous les PDF.
Un premier contrôle réel du 02/08/2026 avait constaté un refus HTTP 403 sur les
API `bilans` et `actes`. Après la demande des deux bases, un nouveau test a
confirmé leur activation : les deux routes répondent en HTTP 200. Le SIREN de
contrôle retourne zéro bilan et un acte, dont les métadonnées correspondent à
la documentation. La création du modèle documentaire SQLite peut commencer.

Avant le modèle documentaire, une passe d'ergonomie a harmonisé l'interface
locale : contrôles de formulaires, boutons, espacements, panneaux et navigation
active. Les pages Alertes, Imports et Automatisation utilisent maintenant des
grilles adaptées au contenu et aux écrans étroits. Les dates du Planificateur
Windows sont présentées dans un format lisible et la source multisource est
proposée explicitement.

Le modèle documentaire INPI est maintenant implémenté. La collecte conserve
les métadonnées des actes, bilans PDF et bilans saisis dans une table SQLite
dédoublonnée, sans enregistrer leur contenu. La fiche société affiche les
documents disponibles et permet de télécharger chaque PDF à la demande après
une nouvelle authentification INPI. La phase restera en cours jusqu'à la
validation sur une collecte réelle du portefeuille.

La fiche société a ensuite été rééquilibrée à partir du contrôle visuel réel :
marges internes du panneau, grille à trois colonnes, regroupement des champs
longs, cartes homogènes et liens officiels présentés comme des actions. La
grille passe à deux puis une colonne selon la largeur de l'écran.
Chaque ligne du tableau de bord propose maintenant un lien direct « Fiche »,
et le mini-rapport contient une action principale « Ouvrir la fiche société ».

### Phase 13 — Tableau de bord opérationnel — TERMINÉE

- Rechercher par SIREN ou raison sociale et filtrer par modification, erreur,
  état, source ou ancienneté de la dernière vérification.
- Trier les sociétés selon le niveau d'alerte.
- Afficher les volumes surveillés, changements récents, erreurs restantes,
  sociétés jamais collectées et données devenues anciennes.
- Créer une page dédiée aux erreurs et aux reprises ciblées.

État : recherche et filtres par état, modification, erreur, source et
ancienneté, tri par criticité, indicateurs opérationnels, page d'erreurs et
relance asynchrone d'un SIREN sont disponibles.

### Phase 14 — Rapports enrichis — TERMINÉE

- Proposer une synthèse courte et un rapport détaillé par société.
- Ajouter les exports PDF et Excel, une chronologie et la comparaison de deux
  périodes.
- Permettre de sélectionner les sociétés incluses dans un rapport.
- Ajouter un sommaire avec liens internes et enrichir la publication Notion.

État : la synthèse et les fiches détaillées existantes sont complétées par une
sélection des sociétés et des exports Excel/PDF. La chronologie, les rapports
HTML à sommaire et la publication Notion restent intégrés au flux existant.

### Phase 15 — Sauvegarde et restauration web — TERMINÉE

- Afficher la date, l'état et le contenu de la dernière sauvegarde.
- Permettre la création et le téléchargement manuel d'une archive.
- Vérifier périodiquement l'intégrité des sauvegardes.
- Créer un assistant de restauration avec prévisualisation et confirmation,
  sans écraser directement la base active.
- Signaler l'absence de sauvegarde valide.

État : page dédiée, inventaire et contrôle d'intégrité, création et
téléchargement manuel, prévisualisation d'une archive et préparation d'une base
restaurée séparée sans écrasement de la base active.

### Phase 16 — Portefeuilles et catégories — TERMINÉE

- Regrouper les sociétés en portefeuilles tels que clients, fournisseurs,
  concurrents, prospects ou participations.
- Ajouter des étiquettes, un responsable ou un contact interne.
- Importer et exporter un portefeuille complet.
- Appliquer des règles de surveillance adaptées à chaque catégorie.

État : portefeuilles, catégories, responsables, contacts, étiquettes et niveau
de surveillance sont persistés dans SQLite. Affectation web et import/export
CSV sont disponibles.

### Phase 17 — Intégration Windows et ergonomie — TERMINÉE

- Créer un raccourci de lancement et ouvrir automatiquement le navigateur.
- Étudier une icône dans la zone de notification.
- Afficher clairement l'état et la progression d'une collecte.
- Permettre un arrêt propre et afficher les résultats sans lecture du journal
  technique.

État : lanceur Windows avec ouverture automatique du navigateur, progression
par SIREN dans l'interface, résultats d'exécution, reprises ciblées et drapeau
d'arrêt contrôlé entre deux sociétés. L'icône de notification a été étudiée et
écartée à ce stade : elle ajouterait une dépendance et un second processus sans
bénéfice suffisant pour l'application locale mono-utilisateur.

## Partie 4 — Consolidation et maturité du produit

Les phases 18 à 25 ont été validées le 02/08/2026. Elles seront réalisées
dans l'ordre ci-dessous, après les fonctions terminées de la partie précédente.
Toute modification importante de leur périmètre ou inversion de leur ordre
reste soumise à validation préalable.

### Phase 18 — Tableau de bord décisionnel — TERMINÉE

- Améliorer la lecture immédiate de l'état de la veille et des actions à mener.
- Mettre en avant les modifications, alertes, erreurs, retards et données
  devenues anciennes.
- Proposer des indicateurs synthétiques, des filtres et des listes directement
  exploitables.
- Ne pas ajouter de graphiques : privilégier les nombres clés, badges, tableaux
  et listes ordonnées.

État : le tableau de bord présente les alertes nouvelles, erreurs, sociétés
jamais collectées, données de plus de sept jours et une liste d'actions
prioritaires. Chaque ligne indique un score de qualité. Aucun graphique n'a été
ajouté, conformément à la décision prise.

### Phase 19 — Diffusion personnalisée par portefeuille — TERMINÉE

- Produire des synthèses et rapports adaptés à chaque portefeuille.
- Permettre de configurer une adresse de réception différente pour chaque
  portefeuille.
- Conserver un destinataire général de repli lorsqu'aucune adresse particulière
  n'est renseignée.
- Valider les adresses, empêcher les envois en double et journaliser le résultat
  de chaque envoi sans bloquer les autres portefeuilles.
- Ne jamais enregistrer les mots de passe SMTP dans les portefeuilles ; ils
  restent protégés dans le coffre Windows existant.

État : chaque portefeuille accepte une adresse de réception validée. Après la
synthèse générale, l'exécution hebdomadaire produit un rapport limité aux
sociétés du portefeuille et l'envoie à cette adresse. Les résultats d'envoi
sont conservés dans SQLite et une erreur n'interrompt pas les autres envois.

### Phase 20 — Centre documentaire juridique — TERMINÉE

- Centraliser les actes, comptes annuels, annonces et autres documents d'une
  société.
- Améliorer la recherche, le filtrage, le classement et le téléchargement à la
  demande sans téléchargement automatique massif.
- Afficher clairement le type, la date, la source et la disponibilité de chaque
  document.

État : une page Documents réunit les métadonnées INPI de toutes les sociétés,
avec recherche, filtre par type, accès à la fiche et téléchargement PDF à la
demande uniquement.

### Phase 21 — Recherche et navigation transversales — TERMINÉE

- Rechercher depuis un point unique une société, un SIREN, une alerte, un
  document, un portefeuille ou un rapport.
- Faciliter les passages entre tableau de bord, fiche société, erreurs,
  documents et rapports.
- Conserver les filtres utiles lors des retours vers une liste.

État : la recherche globale retrouve sociétés, SIREN, alertes, documents et
rapports depuis un point unique. La navigation principale a été réorganisée
avec un menu Gestion afin de conserver un en-tête lisible.

### Phase 22 — Qualité et traçabilité des données — TERMINÉE

- Rendre visibles la provenance, la date de collecte, l'ancienneté et les
  contradictions de chaque information importante.
- Signaler les données manquantes, incohérentes ou devenues anciennes.
- Faciliter le diagnostic d'une différence entre plusieurs sources.

État : le score de qualité tient compte des champs essentiels absents, des
contradictions et des erreurs de source. Il complète les provenances, dates et
contradictions déjà visibles dans les fiches sociétés.

### Phase 23 — Automatisation et supervision renforcées — TERMINÉE

- Améliorer le suivi des collectes, reprises, publications et envois.
- Différencier clairement les erreurs temporaires, permanentes et de
  configuration.
- Proposer des reprises sûres et ciblées sans rejouer inutilement une collecte
  complète.

État : la supervision distingue les erreurs temporaires, permanentes et
techniques, relie les SIREN aux fiches et les exécutions à leurs rapports. La
page Erreurs permet le diagnostic dépliable et la reprise d'un seul SIREN.

### Phase 24 — Sécurité, confidentialité et audit — TERMINÉE

- Consolider la protection des secrets, des imports, des téléchargements et
  des opérations sensibles.
- Journaliser les actions importantes et les changements de configuration.
- Prévoir la purge et la durée de conservation des journaux, rapports,
  sauvegardes et documents temporaires.

État : un journal d'audit SQLite retrace les imports, relances, arrêts,
téléchargements documentaires, sauvegardes, restaurations et configurations
de destinataires. Sa rétention est limitée à 365 jours. Les protections CSRF,
DPAPI, contrôles de noms de fichiers et en-têtes HTTP restent actives.

### Phase 25 — Stabilisation et distribution — TERMINÉE

- Finaliser l'installation, la mise à jour, la configuration initiale et le
  diagnostic de l'application locale.
- Renforcer les tests fonctionnels, les contrôles de migration SQLite et la
  documentation utilisateur.
- Préparer une version stable, sauvegardable et restaurable sans connaissance
  technique particulière.

État : le schéma SQLite porte la version 25 et conserve les migrations
compatibles avec les bases existantes. Une page Diagnostic contrôle Python,
l'intégrité SQLite, la version du schéma et les dossiers de rapports et de
sauvegardes. Le lanceur Windows, les sauvegardes vérifiées et la suite de tests
constituent le socle de distribution locale stable.

## Partie 5 — Évolutions futures validées

Les phases 26 à 37 proposées lors du cadrage du 02/08/2026 sont validées par
l'utilisateur. Elles devront être réalisées dans l'ordre ci-dessous. Leur
périmètre approuvé ne doit pas être élargi, réduit ou réordonné sans discussion
préalable.

Ces évolutions doivent rester utilisables gratuitement et localement. Aucun
abonnement ni service payant ne sera rendu obligatoire. Une intégration
externe facultative devra toujours posséder un fonctionnement local de repli.

### Phase 26 — Centre de configuration — VALIDÉE, À RÉALISER

- Réunir dans une page unique les réglages actuellement dispersés : sources,
  collecte, courriel, Notion, sauvegardes et conservation des données.
- Afficher pour chaque connecteur son état sans jamais révéler les secrets.
- Proposer un test de connexion ciblé pour INSEE, INPI, BODACC, SMTP et Notion.
- Distinguer clairement les valeurs enregistrées dans SQLite des secrets
  protégés par DPAPI.
- Journaliser les changements de configuration dans l'audit.

Critère de fin : l'installation et la vérification des connecteurs peuvent être
réalisées depuis l'interface, sans modifier manuellement les fichiers Python.

### Phase 27 — Assistant de première utilisation — VALIDÉE, À RÉALISER

- Détecter une base neuve et proposer un parcours guidé non bloquant.
- Guider la configuration des sources gratuites, de l'envoi, de la collecte du
  lundi et de la première sauvegarde.
- Permettre l'ajout manuel d'un premier SIREN ou l'import du modèle Excel.
- Terminer par un diagnostic et une collecte de contrôle sur une société.
- Permettre de quitter puis reprendre l'assistant sans perdre l'avancement.

Critère de fin : un utilisateur non technique peut rendre l'application
opérationnelle en suivant uniquement les indications de l'interface.

### Phase 28 — Profils de surveillance — VALIDÉE, À RÉALISER

- Transformer les niveaux standard, renforcé et critique en profils explicites.
- Associer à chaque profil les sources, catégories d'alertes, profondeur
  documentaire et règles de notification pertinentes.
- Appliquer un profil à une société ou à tout un portefeuille.
- Afficher les exceptions individuelles sans masquer le profil hérité.
- Fournir des profils préconfigurés modifiables sans supprimer les préférences
  déjà enregistrées.

Critère de fin : le niveau de surveillance produit un comportement concret,
compréhensible et couvert par des tests.

### Phase 29 — Calendrier et échéances juridiques — VALIDÉE, À RÉALISER

- Extraire des données disponibles les dates de clôture, dépôt de comptes,
  assemblées, modifications et autres échéances identifiables.
- Présenter une liste chronologique mensuelle, sans graphique.
- Autoriser les échéances internes manuelles avec commentaire et responsable.
- Ajouter des rappels configurables, sans confondre une estimation avec une
  date officielle.
- Exporter le calendrier au format iCalendar (`.ics`).

Critère de fin : les échéances à venir sont consultables, traçables et
exportables, avec indication de leur origine.

### Phase 30 — Tâches et suivi interne — VALIDÉE, À RÉALISER

- Créer une tâche depuis une société, une alerte, un document ou une erreur.
- Gérer un responsable, une échéance, une priorité et les états à faire, en
  cours, en attente et terminée.
- Afficher les tâches ouvertes dans la fiche et le tableau de bord.
- Conserver l'historique des changements d'état dans le journal d'audit.
- Exporter une liste de tâches sans imposer d'outil externe.

Critère de fin : une alerte importante peut être transformée en action suivie
jusqu'à sa clôture.

### Phase 31 — Notes et dossiers de travail — VALIDÉE, À RÉALISER

- Ajouter des notes datées aux sociétés, alertes, documents et tâches.
- Distinguer le commentaire synthétique actuel des notes d'historique.
- Permettre d'épingler une note importante et de rechercher dans leur contenu.
- Autoriser des liens entre sociétés surveillées sans modifier les données
  officielles collectées.
- Inclure les notes uniquement dans les exports explicitement demandés.

Critère de fin : le contexte interne est conservé dans une chronologie
distincte, sauvegardée et auditable.

### Phase 32 — Comparaison documentaire — VALIDÉE, À RÉALISER

- Permettre de sélectionner deux actes ou comptes d'une même société.
- Extraire localement le texte des PDF lorsque le document le permet.
- Mettre en évidence les ajouts, suppressions et changements de passages.
- Signaler clairement les PDF scannés non exploitables sans OCR.
- Ne jamais présenter la comparaison automatique comme une analyse juridique.

Critère de fin : deux versions textuelles peuvent être comparées sans envoyer
les documents vers un service tiers.

### Phase 33 — Règles d'alerte personnalisées — VALIDÉE, À RÉALISER

- Créer des règles simples à partir d'un champ, d'un opérateur et d'une valeur.
- Définir le niveau, le libellé et les destinataires de chaque règle.
- Tester une règle sur l'historique sans créer d'alertes réelles.
- Prévenir les doublons et les règles trop larges ou contradictoires.
- Conserver la version de la règle ayant déclenché chaque alerte.

Critère de fin : une règle peut être créée, simulée, activée et désactivée
depuis l'interface en toute sécurité.

### Phase 34 — Rapports programmables — VALIDÉE, À RÉALISER

- Créer des modèles de rapport associant portefeuille, période, niveaux
  d'alerte, sections et formats de sortie.
- Programmer une diffusion hebdomadaire ou mensuelle indépendante par modèle.
- Prévisualiser le contenu et les destinataires avant activation.
- Conserver le résultat de chaque génération et envoi.
- Empêcher qu'une même exécution adresse deux fois le même rapport au même
  destinataire.

Critère de fin : plusieurs rapports ciblés peuvent coexister sans modifier le
rapport hebdomadaire général.

### Phase 35 — API locale et interopérabilité — VALIDÉE, À RÉALISER

- Exposer une API locale en lecture pour les sociétés, alertes, documents,
  portefeuilles et exécutions.
- Protéger toute écriture par une authentification locale distincte et
  désactivée par défaut.
- Fournir une documentation de l'API et des exemples sans secret.
- Prévoir des exports JSON stables et versionnés.
- Limiter l'écoute au poste local tant qu'un mode réseau n'est pas validé.

Critère de fin : un outil local autorisé peut consulter les données sans accès
direct au fichier SQLite.

### Phase 36 — Accessibilité et finition responsive — VALIDÉE, À RÉALISER

- Auditer toutes les pages au clavier, les libellés, contrastes, messages et
  relations entre contrôles.
- Corriger les tableaux, menus, formulaires et chronologies sur mobile,
  tablette et affichage agrandi.
- Ajouter des liens d'évitement et une gestion cohérente du focus.
- Respecter la réduction des animations demandée par le système.
- Viser les exigences pertinentes du niveau WCAG 2.2 AA.

Critère de fin : les parcours principaux sont utilisables au clavier et aux
largeurs de référence, sans perte d'information ni d'action.

### Phase 37 — Version stable 1.0 et maintenance — VALIDÉE, À RÉALISER

- Geler le schéma fonctionnel de la version 1.0 et documenter ses migrations.
- Créer un installateur ou paquet Windows reproductible avec désinstallation
  et mise à jour préservant les données.
- Effectuer un test complet sur une installation neuve puis sur une mise à
  niveau de la base existante.
- Formaliser la sauvegarde, la restauration, le diagnostic et la procédure de
  retour à la version précédente.
- Publier un guide utilisateur, un guide de maintenance et les limites connues.

Critère de fin : la version 1.0 peut être installée, utilisée, mise à jour et
restaurée sur Windows sans intervention dans le code source.

## Décisions à prendre au moment approprié

- Application locale ou accessible en ligne.
- Utilisateur unique ou plusieurs comptes.
- Suppression définitive ou archivage d'une société.
- Fréquence et horaire des collectes.
- Jour et heure d'envoi du rapport hebdomadaire.
- Destinataires et service utilisé pour l'envoi des e-mails.
- Structure exacte des espaces Notion.
- Durée de conservation des rapports et instantanés.
