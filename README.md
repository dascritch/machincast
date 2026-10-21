# MachinCast

Système automatisé de diffusion sonore pour radio, sous Linux : il fournit un fil antenne en dehors des émissions en direct, à partir de banques de sonores et d'événements horaires.

- **Équipe de l'antenne** : le [guide de l'antenne](doc/utilisateur/README.md), pour programmer et suivre l'antenne depuis l'interface graphique
- **Administrateur du poste** : [INSTALL.md](INSTALL.md) pour l'installation, puis le [guide d'administration](doc/administration/README.md)
- **Développeur** : le [guide du développement](doc/developpement/README.md), avec la [spécification fonctionnelle](doc/spec.md) et les [règles du projet](doc/regles/developpement.md)

## Configuration recommandée

Système Linux graphique, avec le moteur audio PipeWire, idéalement Debian ou Ubuntu LTS, et deux sorties sons distinctes, dont une de qualité pour la sortie antenne.

## Contexte

Je suis animateur bénévole sur [Radio &lt;FMR&gt;](https://radio-fmr.net), radio associative de Toulouse, France.

Cette radio utilise un logiciel d'automatisation d'antenne minimal pour gérer son fil musical continu et les émissions en extérieur. Mais ce logiciel est vieux, n'est plus maintenu, est sous licence propriétaire, est bourré de bugs et manque cruellement de certaines fonctions.

Cela fait plus de 15 années que nous avons successivement tenté de migrer vers différents outils. Soit ils étaient trop compliqués, soit les outils supposés libres se sont refermés et sont devenus des solutions en SaaS.

J'ai estimé qu'il était plus simple de recoder de zéro un tel outil, en connnaissant parfaitement nos usages, les fonctions manquantes et les erreurs de manipulation les plus classiques de ceux qui le gèrent. L'outil ne sert pas à produire une diffusion en stream directement, la sortie sonore d'une carte son professionnelle est envoyée vers une régie finale, et des outils techniques pour les affichages DAB+ et RDS.

Si en tant que radio, autre organisation ou particulier, vous avez décidé d'installer ce logiciel, n'hésitez absolument pas à prendre contact pour parler de votre expérience, ccas d'usage et dans quelle installation vous l'avez inséré.

## Auteurs

- [Xavier Mouton-Dubosc aka `dascritch`](https://dascritch.com)
- Claude.AI

## Licence

[GPLv3](LICENSE)

© Xavier Mouton-Dubosc pour [Radio &lt;FMR&gt;](https://radio-fmr.net)

## Hommage

 - Patrick Chabouté "Docteur rock"
 - Pascal Bouche "Raskal"
 - Fabrice Serin "DJ Tro"

aux animateurs, bénévoles, soutients et aux artistes passés et à venir qui ont fait vivre l'antenne de Radio FMR
