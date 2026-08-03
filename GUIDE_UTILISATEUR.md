# Guide utilisateur — Veille-SIREN 1.0

## Démarrage

1. Exécuter `scripts\lancer_interface.ps1`.
2. Ouvrir `http://127.0.0.1:5000` si le navigateur ne s'ouvre pas.
3. Lors d'une installation neuve, suivre l'assistant « Premiers pas ».

## Parcours principal

- Ajouter une société depuis le tableau de bord ou importer le modèle Excel.
- Configurer les sources gratuites dans « Gestion > Configuration ».
- Conserver la collecte hebdomadaire du lundi à 7 h avec rattrapage Windows.
- Consulter les changements et gérer les alertes depuis la fiche société.
- Organiser les sociétés avec les portefeuilles et profils de surveillance.
- Suivre les échéances, tâches et notes dans le menu « Travail ».
- Télécharger ou comparer les documents INPI uniquement à la demande.
- Créer des règles et rapports ciblés depuis le menu « Gestion ».

## Données et confidentialité

Les données métier restent dans SQLite sur le poste. Les secrets INSEE, INPI,
SMTP et Notion sont protégés par Windows DPAPI. L'API `/api/v1` est en lecture
seule et destinée exclusivement à `127.0.0.1`.

## Sauvegarde

Une archive est créée après chaque chaîne hebdomadaire. Une sauvegarde manuelle
et sa vérification sont disponibles dans « Gestion > Sauvegardes ».
