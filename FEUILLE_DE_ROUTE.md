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

## Phase 7 — Intégration Notion

- Définir les bases ou pages Notion cibles.
- Publier les rapports quotidiens de veille.
- Publier les rapports journaliers de développement.
- Configurer l'authentification de l'application.
- Conserver les identifiants Notion utiles dans SQLite.
- Empêcher les publications en double.
- Gérer les erreurs Notion sans bloquer la collecte.

État : en cours. La connexion au workspace Notion personnel est
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
dans le registre anti-doublon a également été contrôlée. Reste à automatiser
la publication des rapports de développement avant de clôturer la phase. La structure a été
volontairement simplifiée : le Journal ne conserve que le titre, la date et le
statut ; les deux vues portent des noms explicites, sont triées par date
décroissante et n'affichent que les champs utiles. Les métadonnées techniques
restent disponibles pour l'application mais sont masquées dans la vue.

## Phase 8 — Automatisation

- Planifier les collectes quotidiennes.
- Rendre l'heure configurable.
- Générer automatiquement le rapport hebdomadaire.
- Envoyer le rapport hebdomadaire par e-mail aux destinataires configurés.
- Journaliser les succès et les échecs d'envoi sans bloquer les collectes.
- Permettre un lancement manuel depuis l'interface.
- Afficher les dernières et prochaines exécutions.
- Produire un bilan des succès, changements et erreurs.
- Publier automatiquement les rapports.
- Conserver l'historique des exécutions.

## Phase 9 — Déploiement et sécurisation

- Décider si l'application reste locale, fonctionne sur le réseau local ou
  est hébergée en ligne.
- Définir l'authentification et le nombre d'utilisateurs.
- Évaluer une éventuelle migration de SQLite vers PostgreSQL.
- Protéger les secrets et accès Notion.
- Organiser les sauvegardes.
- Sécuriser Playwright et la planification.

## Décisions à prendre au moment approprié

- Application locale ou accessible en ligne.
- Utilisateur unique ou plusieurs comptes.
- Suppression définitive ou archivage d'une société.
- Fréquence et horaire des collectes.
- Jour et heure d'envoi du rapport hebdomadaire.
- Destinataires et service utilisé pour l'envoi des e-mails.
- Structure exacte des espaces Notion.
- Durée de conservation des rapports et instantanés.
