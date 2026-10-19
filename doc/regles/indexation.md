# Règles — Binaire indexation

À lire avant de toucher à `Machin_indexation`. Comportement complet : [spec.md § 6](../spec.md#6-binaire-indexation).

- Deux modes ([#69](https://github.com/dascritch/machincast/issues/69)) : indexation rapide par défaut, qui ne décode que les sonores `apercu` et contrôle seulement la présence des autres fichiers ; audit complet (`--audit-complet`), qui décode tout. Un nouveau fichier est toujours enregistré à l'état `apercu`, sans être décodé.
- Vérifier chaque fichier par **décodage complet** (GStreamer), pas seulement par son extension ou son en-tête : `machincast.indexation.decodage.verifier_fichier`. Ne pas se fier à l'absence d'erreur de GStreamer : examiner aussi les ruptures de continuité et la durée annoncée ([spec.md § 6.1](../spec.md#61-vérification-des-sonores-existants-hors-streams)).
- Un décodeur GStreamer absent n'est jamais la faute du fichier : lever `DecodeurIndisponible` et arrêter, sans changer l'état d'aucun sonore.
- Un décodage bloqué avant le moindre son est repris (jusqu'à trois tentatives) : GStreamer se bloque parfois au démarrage d'un pipeline, et un fichier sain ne doit jamais être déclaré erroné pour cette raison.
- Un fichier défectueux est signalé par son chemin, jamais par l'identifiant du sonore, en anomalie (`logging`, niveau `warning`).
- L'indexeur ne fait que lire les fichiers sonores ([#96](https://github.com/dascritch/machincast/issues/96)) : un fichier introuvable, endommagé ou déplacé change l'état de son sonore, jamais le fichier. Voir [developpement.md](developpement.md#fichiers-sonores).
- États ([#66](https://github.com/dascritch/machincast/issues/66)) : fichier illisible ou endommagé → `errone` ; fichier introuvable → `supprime` ; fichier sain d'un sonore `apercu` ou `errone` → `actif`. Seul un sonore `apercu`, `actif` ou `errone` change d'état : `desactive`, `expire` et `supprime` sont conservés, le fichier défectueux est quand même signalé sur STDERR.
- Fichier dont la date de modification ou la taille a changé : revérifier, mettre à jour durée et tags.
- **Ne jamais modifier un champ listé dans `sonores.champs_edites`** : l'édition manuelle prime. Une clé des métadonnées musicales y figure sous la forme `metadonnees_musicales.<clé>`.
- Tags ([#8](https://github.com/dascritch/machincast/issues/8)) : lus pendant le décodage de la vérification (`machincast.indexation.tags`), jamais par une seconde lecture du fichier. L'indexeur ne tient que les clés `machincast.indexation.tags.CLES` de `metadonnees_musicales` ; les autres clés ne sont jamais touchées.
- L'année ne vient jamais d'un horodatage avec heure : c'est une date de création, pas de sortie.
- L'indexeur ne rétablit que les sonores qu'il a lui-même déclarés `errone`.
- Connexion par `machincast.base.connecter(…, Role.INDEXATION)` ; une transaction par sonore, pour qu'une interruption garde le travail fait.
- Parcours récursif de tous les répertoires de chaque banque (table `banques_repertoires`), dans `machincast.indexation.repertoires`, avant la vérification : `machincast.indexation.indexeur.indexer` enchaîne les deux. Formats : `repertoires.EXTENSIONS`, casse ignorée ; fichiers et répertoires cachés ignorés ; liens vers des sous-répertoires non suivis ([#9](https://github.com/dascritch/machincast/issues/9)).
- Un nouveau sonore est enregistré à l'état `apercu`, puis rattaché à sa banque en fin de liste. Un emplacement n'est jamais enregistré deux fois ; un sonore connu trouvé dans le répertoire d'une banque y est rattaché s'il n'y est pas.
- Un parcours ordonné (tri des noms) : positions et bilan sont reproductibles.
- Les streams ne sont jamais vérifiés par l'indexeur.
- `verifier_sonores` se limite aux sonores donnés par `identifiants` : l'interface s'en sert pour vérifier aussitôt les fichiers qu'elle ajoute, avec le rôle de l'indexation, dans un fil à part ([#30](https://github.com/dascritch/machincast/issues/30)). Sans eux, il vérifie tous les sonores.
- L'interface lance aussi `indexer` elle-même, depuis son menu « Maintenance » ([#38](https://github.com/dascritch/machincast/issues/38)), et montre ses anomalies en les recueillant dans le journal `machincast.indexation` : une anomalie s'y journalise toujours (`warning`), jamais par `print`, et commence par le chemin du fichier.
- Sorties : STDOUT, STDERR, CSV, HTML. **Jamais d'écriture dans `log`.**
