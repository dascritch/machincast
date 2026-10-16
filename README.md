# MachinCast

Système automatisé de diffusion sonore pour radio, sous Linux : il fournit un fil antenne en dehors des émissions en direct, à partir de banques de sonores et d'événements horaires.

- **Installation** : [INSTALL.md](INSTALL.md)
- **Utilisation** : [guide d'utilisation](doc/utilisation.md)
- **Spécification fonctionnelle** : [doc/spec.md](doc/spec.md)
- **Règles de développement** : [doc/regles](doc/regles/developpement.md)



## Contexte

Je suis animateur bénévole sur [Radio &lt;FMR&gt;](https://radio-fmr.net), radio associative de Toulouse, France.

Cette radio utilise un logiciel d'automatisation d'antenne minimal pour gérer son fil musical continu et les émissions en extérieur. Mais ce logiciel est vieux, n'est plus maintenu, est sous licence propriétaire, est bourré de bugs et  manque cruellement de certaines fonctions.

Cela fait plus de 15 années que nous avons successivement tenté de migrer vers différents outils. Soit ils étaient trop compliqués, soit les outils supposés libres se sont refermés et sont devenus des solutions en SaaS.

J'ai estimé qu'il était plus simple de recoder de zéro un tel outil, en connnaissant parfaitement nos usages, les fonctions manquantes et les erreurs de manipulation les plus classiques de ceux qui le gèrent.

## Auteurs

- [Xavier Mouton-Dubosc aka `dascritch`](https://dascritch.com)
- Claude.AI

## Licence

[GPLv3](LICENSE)

© Xavier Mouton-Dubosc
