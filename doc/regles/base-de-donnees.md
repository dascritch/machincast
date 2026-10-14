# Règles — Base de données

À lire avant de toucher au schéma, aux requêtes ou aux droits. Modèle complet : [spec.md § 3](../spec.md#3-base-de-données).

## Principes

- PostgreSQL, accès par socket Unix locale avec psycopg 3.
- Authentification **peer** : chaque rôle correspond à un utilisateur système.
- Deux bases au schéma strictement identique : production et test.

## Migrations

- Tout changement de schéma passe par une migration **yoyo-migrations** versionnée dans `migrations/`. Jamais de modification manuelle.
- Une migration doit pouvoir s'appliquer aux deux bases sans modification.

## Droits

Le tableau des droits par binaire est dans [spec.md § 3.2](../spec.md#32-rôles-et-droits). Il est appliqué deux fois :

1. en base, par les `GRANT` des rôles ;
2. dans le code : chaque binaire n'exécute que les requêtes autorisées à son rôle.

Points sensibles :

- `Machin_lecture` n'écrit dans `sonores` que le champ `actif`. Dans `airplay` et `log`, il ne fait que des insertions.
- `Machin_indexation` n'écrit que dans `sonores` et `banques_sonores`, et jamais dans `log`.
- En mode simulation, `Machin_lecture` n'écrit **rien** en base.

## Intégrité

- Les lignes `airplay` ne sont jamais supprimées. Elles recopient emplacement, artiste et titre au moment du passage.
- Les contraintes « exactement un des deux » (stream : URL ou marque-page ; élément d'événement : banque ou sonore) sont posées en base par des `CHECK`.
- Les champs listés dans `sonores.champs_edites` ne sont jamais modifiés par l'indexeur.
