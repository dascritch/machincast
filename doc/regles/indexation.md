# Règles — Binaire indexation

À lire avant de toucher à `Machin_indexation`. Comportement complet : [spec.md § 6](../spec.md#6-binaire-indexation).

- Vérifier chaque fichier par **décodage complet** (GStreamer), pas seulement par son extension ou son en-tête : `machincast.indexation.decodage.verifier_fichier`. Ne pas se fier à l'absence d'erreur de GStreamer : examiner aussi les ruptures de continuité et la durée annoncée ([spec.md § 6.1](../spec.md#61-vérification-des-sonores-existants-hors-streams)).
- Un décodeur GStreamer absent n'est jamais la faute du fichier : lever `DecodeurIndisponible` et arrêter, sans désactiver de sonore.
- Un décodage bloqué avant le moindre son est repris (jusqu'à trois tentatives) : GStreamer se bloque parfois au démarrage d'un pipeline, et un fichier sain ne doit jamais être désactivé pour cette raison.
- Un fichier défectueux est signalé par son chemin, jamais par l'identifiant du sonore, en anomalie (`logging`, niveau `warning`).
- Fichier illisible, endommagé, supprimé ou déplacé : passer le sonore inactif et le signaler sur STDERR.
- Fichier dont la date de modification ou la taille a changé : revérifier, mettre à jour durée et tags.
- **Ne jamais modifier un champ listé dans `sonores.champs_edites`** : l'édition manuelle prime. Seule exception : un fichier défectueux désactive son sonore même si `actif` a été édité à la main.
- L'indexeur ne réactive jamais un sonore.
- Connexion par `machincast.base.connecter(…, Role.INDEXATION)` ; une transaction par sonore, pour qu'une interruption garde le travail fait.
- Parcours récursif de tous les répertoires de chaque banque (table `banques_repertoires`). Formats : mp3, m4a, ogg, flac, wav, aiff.
- Un nouveau sonore est rattaché à sa banque en fin de liste.
- Les streams ne sont jamais vérifiés par l'indexeur.
- Sorties : STDOUT, STDERR, CSV, HTML. **Jamais d'écriture dans `log`.**
