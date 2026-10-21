# Guide du développement

Ce guide s'adresse aux développeurs de MachinCast. L'usage de l'interface est décrit dans le [guide de l'antenne](../utilisateur/README.md), l'installation et l'exploitation du poste dans le [guide d'administration](../administration/README.md).

- [Poste de développement](poste.md) : installer les outils, lancer les tests, refaire les captures d'écran du guide de l'antenne.
- [Spécification fonctionnelle](../spec.md) : le comportement visé, et sa mise en œuvre, ticket par ticket.
- **Règles du projet**, à lire avant de modifier le code concerné :
  - [Développement](../regles/developpement.md) : tickets, commits, style, definition of done, et où va la documentation ;
  - [Tests](../regles/tests.md) ;
  - [Base de données](../regles/base-de-donnees.md) ;
  - [Machin lecture](../regles/binaire-lecture.md) ;
  - [Machin indexation](../regles/indexation.md) ;
  - [Machin interface](../regles/interface.md) ;
  - [Wrapper Machin, configuration, install.sh](../regles/wrapper.md).
- [CLAUDE.md](../../CLAUDE.md) : les commandes du dépôt, en résumé.
- Les tickets : [GitHub Issues](https://github.com/dascritch/machincast/issues).

## Où va la documentation

Chaque public a son guide ([#128](https://github.com/dascritch/machincast/issues/128)) :

| Public | Guide | Ce qu'il contient |
| --- | --- | --- |
| Équipe de l'antenne | [doc/utilisateur](../utilisateur/README.md) | Le métier de l'antenne et l'interface graphique, avec ses captures d'écran, sans commande à taper. Le menu **Aide → Documentation** l'ouvre. |
| Administrateur du poste | [INSTALL.md](../../INSTALL.md) et [doc/administration](../administration/README.md) | L'installation, les commandes, la configuration, l'indexation et la diffusion en ligne de commande, les messages et les droits. |
| Développeur | ce guide | Le poste de développement, la spécification et les règles. |

`doc/utilisation.md`, l'ancien guide, n'est plus qu'un index vers ces trois guides.
