# Guide de maintenance — Veille-SIREN 1.0

## Contrôles réguliers

- Ouvrir « Diagnostic » et vérifier SQLite, Python, rapports et sauvegardes.
- Tester les connecteurs depuis le Centre de configuration.
- Vérifier l'état et la prochaine exécution de la tâche Windows.
- Lancer `python -m unittest discover -s tests -q` après une mise à jour.

## Mise à niveau

Le schéma SQLite est versionné par `PRAGMA user_version`. La version 1.0 utilise
le schéma 37. `initialiser_base()` applique uniquement des créations additives
et conserve les tables et colonnes existantes.

Avant une mise à niveau, exécuter `scripts\mettre_a_jour.ps1`. Le script crée
une sauvegarde, installe les dépendances figées puis initialise les migrations.

## Retour arrière

1. Arrêter Flask et la tâche Windows.
2. Conserver une copie de la base active.
3. Restaurer l'archive créée avant la mise à jour dans une base séparée depuis
   l'interface de restauration.
4. Réinstaller la version précédente du code puis valider le diagnostic.

Ne jamais remplacer manuellement la base active sans sauvegarde vérifiée.
