# Suivi du temps de développement

Les durées antérieures au démarrage du suivi automatique sont des estimations.

## Sessions de développement

Les heures des sessions des 28, 29 et 30 juillet ont été reconstituées à
partir des durées suivies et des commits de clôture. Elles sont donc
approximatives. À partir de maintenant, les heures de début et de fin sont
relevées directement.

Les périodes de travail d'une même journée sont regroupées dans une seule
session lorsque l'interruption entre elles est strictement inférieure à
30 minutes. Une interruption supérieure ou égale à 30 minutes ouvre une
nouvelle session. La durée correspond à la somme du temps réellement travaillé
et n'inclut pas les interruptions.

| Session | Date | Heure de début | Heure de fin | Durée | Précision |
|---|---|---:|---:|---:|---|
| 1 | 28/07/2026 | ≈ 17:57 | 19:32 | ≈ 1 h 35 | Reconstituée |
| 2 | 29/07/2026 | ≈ 17:36 | 20:21 | ≈ 2 h 45 | Reconstituée |
| 3 | 30/07/2026 | ≈ 16:12 | 19:36 | ≈ 3 h 21 | Mixte |
| 4 | 31/07/2026 | 17:36 | 18:53 | ≈ 1 h 15 | Relevée |
| 5 | 31/07/2026 | 19:28 | 19:48 | ≈ 15 min | Relevée |
| 6 | 01/08/2026 | 12:42 | 14:11 | ≈ 1 h 29 | Relevée |

## Détail des travaux

| Date | Version | Travail réalisé | Durée | Cumul |
|---|---|---|---:|---:|
| 28/07/2026 | Pré-0.2 | Git, branches, nettoyage, refactorisation Pappers, forme juridique, capital et adresse | ≈ 1 h 20 | ≈ 1 h 20 |
| 28/07/2026 | Pré-0.2 | Validation et commit du collecteur existant, extraction et tests des dirigeants, clôture de séance | ≈ 15 min | ≈ 1 h 35 |
| 29/07/2026 | Pré-0.2 | Extraction et affichage du statut INSEE Pappers, tests unitaires et contrôle sur le DOM réel, configuration des exclusions Git | ≈ 20 min | ≈ 1 h 55 |
| 29/07/2026 | Pré-0.2 | Correction du statut synthétique Pappers, extraction et validation réelle de la dernière publication BODACC | ≈ 10 min | ≈ 2 h 05 |
| 29/07/2026 | Pré-0.2 | Extraction, affichage et validation du résumé du dernier changement BODACC | ≈ 10 min | ≈ 2 h 15 |
| 29/07/2026 | Pré-0.2 | Collecte de toutes les sociétés actives, tolérance aux erreurs et compatibilité d'affichage Windows | ≈ 10 min | ≈ 2 h 25 |
| 29/07/2026 | Pré-0.2 | Intégration et tests de la journalisation des collectes et des erreurs | ≈ 10 min | ≈ 2 h 35 |
| 29/07/2026 | Pré-0.2 | Limitation et rotation automatique du fichier de journalisation | ≈ 5 min | ≈ 2 h 40 |
| 29/07/2026 | Pré-0.2 | Création de la base SQLite et enregistrement historique des collectes | ≈ 15 min | ≈ 2 h 55 |
| 29/07/2026 | Pré-0.2 | Comparaison des instantanés et détection automatique des changements | ≈ 15 min | ≈ 3 h 10 |
| 29/07/2026 | Pré-0.2 | Génération de rapports Markdown récapitulant les collectes et changements | ≈ 15 min | ≈ 3 h 25 |
| 29/07/2026 | Pré-0.2 | Fiabilisation de la navigation Pappers et fermeture garantie de Chromium | ≈ 10 min | ≈ 3 h 35 |
| 29/07/2026 | Pré-0.2 | Validation globale, nettoyage des artefacts suivis et consolidation Git | ≈ 5 min | ≈ 3 h 40 |
| 29/07/2026 | Pré-0.2 | Formalisation et sauvegarde de la feuille de route produit | ≈ 5 min | ≈ 3 h 45 |
| 29/07/2026 | Pré-0.2 | Ajout de l'envoi hebdomadaire des rapports par e-mail à la feuille de route | ≈ 5 min | ≈ 3 h 50 |
| 29/07/2026 | Pré-0.2 | Déplacement du projet vers Google Drive, réparation et assainissement du dépôt Git, recréation de l'environnement Python, tests et sauvegarde en ligne | ≈ 30 min | ≈ 4 h 20 |
| 30/07/2026 | Pré-0.2 | Phase 1 : modèle SQLite des sociétés surveillées, services CRUD, archivage logique, prévention des doublons et source des collectes | ≈ 25 min | ≈ 4 h 45 |
| 30/07/2026 | Pré-0.2 | Phase 1 : opérations explicites d'activation, de désactivation et de restauration après archivage, avec tests | ≈ 10 min | ≈ 4 h 55 |
| 30/07/2026 | Pré-0.2 | Clôture de la phase 1 et début de la phase 2 : analyse, prévisualisation et import Excel transactionnel avec bilan | ≈ 20 min | ≈ 5 h 15 |
| 30/07/2026 | Pré-0.2 | Phase 2 : consolidation des contrôles Excel, compatibilité de l'ancien lecteur et tests de l'import direct | ≈ 10 min | ≈ 5 h 25 |
| 30/07/2026 | Pré-0.2 | Phase 2 : analyse sécurisée en mémoire des fichiers téléversés et gestion des classeurs vides ou corrompus | ≈ 10 min | ≈ 5 h 35 |
| 30/07/2026 | Pré-0.2 | Début de la phase 3 : installation de Flask, fabrique d'application, tableau de bord et liste des sociétés | ≈ 20 min | ≈ 5 h 55 |
| 30/07/2026 | Pré-0.2 | Phase 3 : nom des sociétés, colonne de modification et mini-rapports dépliables | ≈ 20 min | ≈ 6 h 15 |
| 30/07/2026 | Pré-0.2 | Phase 3 : colonne « Dernière modification » fondée sur la date de publication BODACC | ≈ 5 min | ≈ 6 h 20 |
| 30/07/2026 | Pré-0.2 | Phase 3 : mise en évidence en gras de l'objet de la dernière modification dans le mini-rapport | ≈ 5 min | ≈ 6 h 25 |
| 30/07/2026 | Pré-0.2 | Phase 3 : gestion web des sociétés et protection des actions par jeton CSRF | ≈ 25 min | ≈ 6 h 50 |
| 30/07/2026 | Pré-0.2 | Phase 3 : import Excel web avec prévisualisation et confirmation avant écriture | ≈ 20 min | ≈ 7 h 10 |
| 30/07/2026 | Pré-0.2 | Phase 3 : historique web des collectes et détail des changements par société | ≈ 20 min | ≈ 7 h 30 |
| 30/07/2026 | Pré-0.2 | Clôture de séance : rapport journalier, validation globale et sauvegarde Git | ≈ 10 min | ≈ 7 h 40 |
| 30/07/2026 | Pré-0.2 | Amélioration du suivi avec les dates et heures de début et de fin des sessions | ≈ 1 min | ≈ 7 h 41 |
| 31/07/2026 | Pré-0.2 | Phase 3 : consultation des collectes, du journal et des rapports, confirmation d'archivage, tests et contrôle visuel | ≈ 7 min | ≈ 7 h 48 |
| 31/07/2026 | Pré-0.2 | Nettoyage du dépôt : retrait des caches compilés suivis, de l'environnement incomplet et d'un ancien script manuel | ≈ 2 min | ≈ 7 h 50 |
| 31/07/2026 | Pré-0.2 | Phase 4 : navigateur mutualisé, modes visible et sans interface, suivi SQLite des tâches, nouvelles tentatives et verrouillage par SIREN | ≈ 4 min | ≈ 7 h 54 |
| 31/07/2026 | Pré-0.2 | Regroupement des sessions quotidiennes séparées par moins de 30 minutes | ≈ 3 min | ≈ 7 h 57 |
| 31/07/2026 | Pré-0.2 | Phase 4 : abstraction du contrat des sources de collecte et implémentation Pappers indépendante | ≈ 2 min | ≈ 7 h 59 |
| 31/07/2026 | Pré-0.2 | Phase 4 : ajout des sources officielles INSEE, INPI et BODACC, configuration sécurisée, tests et validation BODACC réelle | ≈ 6 min | ≈ 8 h 05 |
| 31/07/2026 | Pré-0.2 | Diagnostic réel de l'authentification INPI et identification de l'activation d'accès API manquante | ≈ 6 min | ≈ 8 h 11 |
| 31/07/2026 | Pré-0.2 | Création de l'application INSEE, souscription à API Sirene 3.11, stockage DPAPI de la clé et validation réelle de la collecte | ≈ 45 min | ≈ 8 h 56 |
| 31/07/2026 | Pré-0.2 | Tableau de bord : remplacement de la date de modification de la fiche par l'horodatage explicite de la dernière collecte, validation et clôture | ≈ 8 min | ≈ 9 h 04 |
| 31/07/2026 | Pré-0.2 | Déplacement de l'import Excel vers une page « Imports » dédiée et planification de la validation INPI | ≈ 7 min | ≈ 9 h 11 |
| 01/08/2026 | Pré-0.2 | Coffre Windows DPAPI pour les identifiants INPI, chargement automatique, documentation et tests | ≈ 3 min | ≈ 9 h 14 |
| 01/08/2026 | Pré-0.2 | Test réel INPI : coffre validé, authentification refusée en HTTP 401 et diagnostic de l'accès API | ≈ 3 min | ≈ 9 h 17 |
| 01/08/2026 | Pré-0.2 | Nouveau test INPI : identifiants acceptés mais type de connexion API non autorisé en HTTP 403 | ≈ 2 min | ≈ 9 h 19 |
| 01/08/2026 | Pré-0.2 | Activation de l'accès API RNE, adaptation à la réponse JSON réelle et validation complète de la collecte INPI | ≈ 9 min | ≈ 9 h 28 |
| 01/08/2026 | Pré-0.2 | Phase 5 : rapport HTML principal, Markdown secondaire, synthèse d'exécution, changements avant/après et consultation web | ≈ 6 min | ≈ 9 h 34 |
| 01/08/2026 | Pré-0.2 | Phase 5 : synthèse hebdomadaire HTML depuis SQLite, comparaison sur sept jours, erreurs et commande dédiée | ≈ 8 min | ≈ 9 h 42 |
| 01/08/2026 | Pré-0.2 | Clôture de la phase 5 : conservation 365 jours avec nettoyage ciblé et protection illimitée des rapports de développement | ≈ 18 min | ≈ 10 h 00 |
| 01/08/2026 | Pré-0.2 | Phase 6 : harmonisation des rapports de développement, contrôle automatique et cadrage initial de Notion | ≈ 3 min | ≈ 10 h 03 |
| 01/08/2026 | Pré-0.2 | Phase 7 : création de la base Notion des rapports de veille, cibles SQLite et registre anti-doublon | ≈ 3 min | ≈ 10 h 06 |
| 01/08/2026 | Pré-0.2 | Nettoyage Notion : simplification du Journal et des vues Veille-SIREN sans suppression de contenu | ≈ 3 min | ≈ 10 h 09 |
| 01/08/2026 | Pré-0.2 | Centralisation des comptes rendus dans « Journal de travail » et retrait des anciennes bases Notion de démonstration | ≈ 3 min | ≈ 10 h 12 |
| 01/08/2026 | Pré-0.2 | Phase 7 : coffre DPAPI Notion, client HTTP, publication quotidienne, anti-doublon et tolérance aux erreurs | ≈ 7 min | ≈ 10 h 19 |
| 01/08/2026 | Pré-0.2 | Validation du jeton Notion, normalisation des identifiants de source et diagnostic de l'accès à la base | ≈ 14 min | ≈ 10 h 33 |
| 01/08/2026 | Pré-0.2 | Première publication Notion réelle depuis quatre instantanés SQLite et validation de l'anti-doublon | ≈ 5 min | ≈ 10 h 38 |
| 01/08/2026 | Pré-0.2 | Clôture de session, validation globale et sauvegarde GitHub | ≈ 2 min | ≈ 10 h 40 |

## Total par version

| Version | Durée |
|---|---:|
| Pré-0.2 | ≈ 10 h 40 |
