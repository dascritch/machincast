# Règles — Binaire indexation

À lire avant de toucher à `Machin_indexation`. Comportement complet : [spec.md § 6](../spec.md#6-binaire-indexation).

- Vérifier chaque fichier par **décodage complet** (GStreamer), pas seulement par son extension ou son en-tête.
- Fichier illisible, endommagé, supprimé ou déplacé : passer le sonore inactif et le signaler sur STDERR.
- Fichier dont la date de modification ou la taille a changé : revérifier, mettre à jour durée et tags.
- **Ne jamais modifier un champ listé dans `sonores.champs_edites`** : l'édition manuelle prime.
- Parcours récursif de tous les répertoires de chaque banque (table `banques_repertoires`). Formats : mp3, m4a, ogg, flac, wav, aiff.
- Un nouveau sonore est rattaché à sa banque en fin de liste.
- Les streams ne sont jamais vérifiés par l'indexeur.
- Sorties : STDOUT, STDERR, CSV, HTML. **Jamais d'écriture dans `log`.**
