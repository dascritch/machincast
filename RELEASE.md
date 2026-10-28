# Versions de MachinCast

Les versions publiées, la plus récente d'abord. Procédure : [doc/developpement/release.md](doc/developpement/release.md).

## 0.9.0 — 2026-10-28

Première version publiée, avant la 1.0 : tout ce que fait MachinCast, fonctionnalité par fonctionnalité.

### Diffusion à l'antenne : Machin lecture

- L'événement actif, selon les priorités et les horaires de la grille ([#12](https://github.com/dascritch/machincast/issues/12)), et le choix d'un sonore dans une banque, séquentielle ou aléatoire ([#13](https://github.com/dascritch/machincast/issues/13)).
- Le déroulé de la liste de lecture d'un événement, et les transitions d'un événement à l'autre ([#14](https://github.com/dascritch/machincast/issues/14)), par la boucle de diffusion ([#88](https://github.com/dascritch/machincast/issues/88)).
- Le moteur audio GStreamer, avec crossfades ([#15](https://github.com/dascritch/machincast/issues/15)), et la position des fondus par rapport aux silences d'un sonore ([#234](https://github.com/dascritch/machincast/issues/234)).
- Les streams, leur chute et leur reprise, et leur événement de secours ([#16](https://github.com/dascritch/machincast/issues/16)).
- L'airplay et le log ([#17](https://github.com/dascritch/machincast/issues/17)), avec les débuts et fins d'événements et de séquences ([#153](https://github.com/dascritch/machincast/issues/153)).
- L'expiration automatique des sonores ([#18](https://github.com/dascritch/machincast/issues/18)).
- Le masquage des métadonnées, et les sorties : airplay en CSV, playlist `.pls` et page HTML publique ([#19](https://github.com/dascritch/machincast/issues/19)).
- La socket d'état, que suit l'interface ([#20](https://github.com/dascritch/machincast/issues/20)).
- La simulation d'une période de diffusion ([#21](https://github.com/dascritch/machincast/issues/21)).
- La banque « ne pas répéter » ([#63](https://github.com/dascritch/machincast/issues/63)), et les séquences, suites de sonores et de banques réutilisables ([#99](https://github.com/dascritch/machincast/issues/99)).
- La playlist immédiate : le prochain sonore et ceux qui suivent, réservés à l'avance ([#228](https://github.com/dascritch/machincast/issues/228)).
- Un sonore joué sans ses silences au début et à la fin ([#146](https://github.com/dascritch/machincast/issues/146)).
- L'analyse au dernier moment d'un sonore jamais vérifié en entier ([#181](https://github.com/dascritch/machincast/issues/181)).
- Le blanc dans un sonore, noté, et qui peut faire passer au secours ([#122](https://github.com/dascritch/machincast/issues/122)).
- Le nom de MachinCast dans le réglage du son du bureau, sous PipeWire et PulseAudio ([#296](https://github.com/dascritch/machincast/issues/296)).

### Programmation et antenne, depuis l'interface

- L'écran d'accueil : sonore en cours, prochain sonore, airplay ([#23](https://github.com/dascritch/machincast/issues/23), [#144](https://github.com/dascritch/machincast/issues/144)), avec les frises du sonore en cours et du suivant ([#230](https://github.com/dascritch/machincast/issues/230)), les sonores à venir, et un onglet Airplay réglable et exportable ([#244](https://github.com/dascritch/machincast/issues/244)).
- Le VU-mètre de l'antenne, avec ses voyants « Saturation » et « Blanc » ([#24](https://github.com/dascritch/machincast/issues/24), [#191](https://github.com/dascritch/machincast/issues/191)).
- Le pilotage du service de diffusion ([#25](https://github.com/dascritch/machincast/issues/25)).
- L'interruption de l'antenne : sauter le sonore, la séquence ou l'événement ([#104](https://github.com/dascritch/machincast/issues/104)), et avancer l'événement suivant ([#257](https://github.com/dascritch/machincast/issues/257)).
- Le calendrier de la grille ([#36](https://github.com/dascritch/machincast/issues/36)), à la semaine ([#118](https://github.com/dascritch/machincast/issues/118)), aux couleurs des types d'événements ([#293](https://github.com/dascritch/machincast/issues/293)), en onglet permanent ([#307](https://github.com/dascritch/machincast/issues/307)).
- Sauter une session d'un événement récurrent, et la rétablir ([#273](https://github.com/dascritch/machincast/issues/273), [#295](https://github.com/dascritch/machincast/issues/295)).
- Une modification de la grille vaut aussitôt à l'antenne ([#266](https://github.com/dascritch/machincast/issues/266)).
- La garantie d'un fil musical ([#39](https://github.com/dascritch/machincast/issues/39)), et les suggestions au lancement ([#119](https://github.com/dascritch/machincast/issues/119), [#231](https://github.com/dascritch/machincast/issues/231)).
- L'écran des incidents ([#35](https://github.com/dascritch/machincast/issues/35)) et l'écran de simulation ([#37](https://github.com/dascritch/machincast/issues/37)).

### Sonores, banques, séquences, événements et feeds

- Les listes avec recherche ([#26](https://github.com/dascritch/machincast/issues/26)), la sélection multiple ([#114](https://github.com/dascritch/machincast/issues/114)), le tri des durées, des dates et des priorités ([#272](https://github.com/dascritch/machincast/issues/272), [#302](https://github.com/dascritch/machincast/issues/302)), et la recherche globale ([#27](https://github.com/dascritch/machincast/issues/27), [#105](https://github.com/dascritch/machincast/issues/105)).
- Les fiches d'un sonore ([#28](https://github.com/dascritch/machincast/issues/28), [#125](https://github.com/dascritch/machincast/issues/125)), d'une banque ([#31](https://github.com/dascritch/machincast/issues/31), [#143](https://github.com/dascritch/machincast/issues/143)), d'un événement ([#32](https://github.com/dascritch/machincast/issues/32), [#140](https://github.com/dascritch/machincast/issues/140)) et d'une séquence ([#112](https://github.com/dascritch/machincast/issues/112), [#138](https://github.com/dascritch/machincast/issues/138)), avec leurs erreurs de saisie mises en avant ([#270](https://github.com/dascritch/machincast/issues/270)).
- Les feeds, adresses de streams réutilisables ([#34](https://github.com/dascritch/machincast/issues/34), [#252](https://github.com/dascritch/machincast/issues/252)).
- L'ajout de sonores ([#30](https://github.com/dascritch/machincast/issues/30)), et la duplication d'un événement, d'une séquence ou d'une banque ([#130](https://github.com/dascritch/machincast/issues/130)).
- La suppression avec ses références ([#33](https://github.com/dascritch/machincast/issues/33)), différée et restaurable ([#267](https://github.com/dascritch/machincast/issues/267)) ; un fichier sonore n'est jamais supprimé ([#96](https://github.com/dascritch/machincast/issues/96)).
- Les durées minimale et maximale des sonores d'une banque ([#147](https://github.com/dascritch/machincast/issues/147), [#210](https://github.com/dascritch/machincast/issues/210)).
- La pré-écoute sur une sortie distincte ([#29](https://github.com/dascritch/machincast/issues/29), [#116](https://github.com/dascritch/machincast/issues/116)), avec la frise du fichier ([#224](https://github.com/dascritch/machincast/issues/224)), depuis toute ligne de sonore ([#226](https://github.com/dascritch/machincast/issues/226)), et la pré-écoute de l'antenne ([#245](https://github.com/dascritch/machincast/issues/245), [#256](https://github.com/dascritch/machincast/issues/256)).
- Les textes saisis nettoyés à l'enregistrement ([#108](https://github.com/dascritch/machincast/issues/108)).

### L'interface au quotidien

- Le menu général ([#117](https://github.com/dascritch/machincast/issues/117)) et les préférences : crossfades par défaut, périphériques, seuils ([#145](https://github.com/dascritch/machincast/issues/145)).
- Les onglets ouverts à la demande ([#180](https://github.com/dascritch/machincast/issues/180)), leurs raccourcis clavier ([#192](https://github.com/dascritch/machincast/issues/192)), et leur rafraîchissement ([#148](https://github.com/dascritch/machincast/issues/148)).
- Les colonnes des tableaux, ajustées, réordonnables, masquables et retenues ([#207](https://github.com/dascritch/machincast/issues/207)).
- Les emoji qui soulignent l'intention des actions ([#294](https://github.com/dascritch/machincast/issues/294)).
- L'icône de l'application, au choix, et le raccourci de bureau ([#62](https://github.com/dascritch/machincast/issues/62), [#111](https://github.com/dascritch/machincast/issues/111), [#213](https://github.com/dascritch/machincast/issues/213)).

### Indexation des sonores

- La vérification d'un fichier par décodage complet, et sa durée ([#7](https://github.com/dascritch/machincast/issues/7)) ; la lecture de ses tags ([#8](https://github.com/dascritch/machincast/issues/8)) ; son type réel ([#121](https://github.com/dascritch/machincast/issues/121)).
- L'indexation récursive des répertoires de banques ([#9](https://github.com/dascritch/machincast/issues/9)), qui repère les fichiers supprimés, déplacés ou modifiés ([#10](https://github.com/dascritch/machincast/issues/10)), et ajoute ou retire un sonore d'une banque selon sa durée ([#195](https://github.com/dascritch/machincast/issues/195)).
- Le document d'audit des anomalies, en CSV et HTML ([#11](https://github.com/dascritch/machincast/issues/11)), et le journal de l'indexation ([#120](https://github.com/dascritch/machincast/issues/120)).
- Les états d'un sonore ([#66](https://github.com/dascritch/machincast/issues/66)), l'indexation rapide et l'audit complet ([#69](https://github.com/dascritch/machincast/issues/69)), optimisé ([#206](https://github.com/dascritch/machincast/issues/206)).
- L'indexation lancée depuis l'interface ([#38](https://github.com/dascritch/machincast/issues/38)).

### Installation et administration

- Le script d'installation `install.sh` ([#40](https://github.com/dascritch/machincast/issues/40)), qui interrompt les programmes en cours ([#254](https://github.com/dascritch/machincast/issues/254)), et le service de diffusion systemd ([#22](https://github.com/dascritch/machincast/issues/22)).
- La commande `Machin` : appel des programmes, aide et autocomplétion ([#6](https://github.com/dascritch/machincast/issues/6)), et la configuration `machincast.toml` ([#2](https://github.com/dascritch/machincast/issues/2), [#76](https://github.com/dascritch/machincast/issues/76)).
- La base PostgreSQL, et un rôle par programme ([#3](https://github.com/dascritch/machincast/issues/3), [#4](https://github.com/dascritch/machincast/issues/4)).
- La maintenance de la base : sauvegarde, schéma, optimisation ([#127](https://github.com/dascritch/machincast/issues/127)), et le désherbage de ce qui dépasse la durée de péremption ([#268](https://github.com/dascritch/machincast/issues/268), [#269](https://github.com/dascritch/machincast/issues/269)).
- Les informations de chaque version publiée : nouveautés au lancement, version, guide de la release ([#208](https://github.com/dascritch/machincast/issues/208)), et son archive `.tar.gz` ([#41](https://github.com/dascritch/machincast/issues/41)).

### Merci

À Xavier Mouton-Dubosc ([dascritch](https://github.com/dascritch)), animateur de [Radio &lt;FMR&gt;](https://radio-fmr.net), qui a demandé chacune de ces fonctionnalités, signalé chaque problème et relu chaque changement.
