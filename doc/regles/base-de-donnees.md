# Règles — Base de données

À lire avant de toucher au schéma, aux requêtes ou aux droits. Modèle complet : [spec.md § 3](../spec.md#3-base-de-données).

## Principes

- PostgreSQL, accès par socket Unix locale avec psycopg 3.
- Authentification **peer** : chaque rôle correspond à un utilisateur système.
- Deux bases au schéma strictement identique : production et test.

## Migrations

- Tout changement de schéma passe par une migration **yoyo-migrations** versionnée dans `src/machincast/migrations/` (`NNNN.nom.sql` et son annulation `NNNN.nom.rollback.sql`). Jamais de modification manuelle, jamais de modification d'une migration déjà fusionnée : on en ajoute une nouvelle.
- Les valeurs énumérées sont des types `ENUM` PostgreSQL. Ajouter une valeur se fait par `ALTER TYPE … ADD VALUE` dans une nouvelle migration ; une valeur ne peut pas être retirée sans recréer le type.
- Les métadonnées non critiques d'un sonore vont dans l'objet JSON `metadonnees_musicales`, sans migration ; seules les données utilisées par la diffusion ou les filtres deviennent des colonnes.
- Texte saisi à la main : `varchar(255)` (constante `LONGUEUR_TEXTE_COURT` de `machincast.base`). Chemin, URL ou message libre : `text`.
- Toute nouvelle contrainte s'accompagne d'un scénario qui vérifie qu'elle refuse ce qu'elle doit refuser.
- Une migration doit pouvoir s'appliquer aux deux bases sans modification.

## Droits

Le tableau des droits par binaire est dans [spec.md § 3.2](../spec.md#32-rôles-et-droits). Il est appliqué deux fois :

1. en base, par les `GRANT` de la migration `0002.droits` aux rôles `machincast_lecture`, `machincast_indexation` et `machincast_interface` ;
2. dans le code : chaque binaire n'exécute que les requêtes autorisées à son rôle.

Règles :

- Un binaire ouvre toujours sa connexion avec `machincast.base.connecter(socket, base, Role.…)`, jamais avec `psycopg.connect` directement : sans `SET ROLE`, l'utilisateur n'a aucun droit.
- Tout changement de droits passe par une nouvelle migration et par la matrice de [`tests/features/roles.feature`](../../tests/features/roles.feature), qui vérifie chaque opération de chaque rôle sur chaque table.
- Une nouvelle table n'est accessible à aucun rôle tant qu'une migration ne lui accorde pas de droits.

Points sensibles :

- `Machin_lecture` n'écrit dans `sonores` que le champ `actif`. Dans `airplay` et `log`, il ne fait que des insertions.
- `Machin_indexation` n'écrit que dans `sonores` et `banques_sonores`, et jamais dans `log`.
- En mode simulation, `Machin_lecture` n'écrit **rien** en base.

## Intégrité

- Les lignes `airplay` ne sont jamais supprimées. Elles recopient emplacement, artiste et titre au moment du passage.
- Les contraintes « exactement un des deux » (stream : URL ou marque-page ; élément d'événement : banque ou sonore) sont posées en base par des `CHECK`.
- Les champs listés dans `sonores.champs_edites` ne sont jamais modifiés par l'indexeur.
