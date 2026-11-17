# Versions de MachinCast

*[English version](RELEASE.md)*

Les versions publiées, la plus récente d'abord. Procédure : [doc/fr/developpement/release.md](doc/fr/developpement/release.md).

## 0.9.1 — 2026-11-17

Une version de consolidation : MachinCast parle français et anglais, le service de diffusion tourne sous son propre compte, l'interface gagne en confort, et la base se sauvegarde et se reprend sur un poste neuf.

### À savoir avant de mettre à jour

- **Noms anglais** : les commandes (`Machin player`, `Machin indexer`…), leurs options, les clés de `machincast.toml` et le schéma de la base sont en anglais ([#352](https://github.com/dascritch/machincast/issues/352), [#356](https://github.com/dascritch/machincast/issues/356), [#357](https://github.com/dascritch/machincast/issues/357), [#358](https://github.com/dascritch/machincast/issues/358), [#359](https://github.com/dascritch/machincast/issues/359), [#367](https://github.com/dascritch/machincast/issues/367), [#368](https://github.com/dascritch/machincast/issues/368)). Un ancien `machincast.toml` est refusé, et une base à l'ancien schéma ne se met pas à jour : la configuration se refait depuis le modèle, et les bases se recréent ([Mettre à jour](INSTALL.fr.md#mettre-à-jour)).
- **Service de diffusion** : il tourne désormais sous son propre compte, avec son propre PipeWire, et ne lit plus les répertoires personnels ; `./install.sh --service` le met à jour, et propose de déplacer MachinCast et les sonores hors d'un répertoire personnel ([#381](https://github.com/dascritch/machincast/issues/381), [#376](https://github.com/dascritch/machincast/issues/376)).

### Langues

- L'interface, les messages, l'aide, `Machin` et `install.sh` parlent la langue de la session, français ou anglais ([#360](https://github.com/dascritch/machincast/issues/360)) ; les nouveautés de la version aussi ([#369](https://github.com/dascritch/machincast/issues/369)).
- Les documents de premier niveau sont en anglais, avec leur source française, et la documentation se range par langue ([#355](https://github.com/dascritch/machincast/issues/355)) ; le guide de l'antenne et le guide d'administration sont traduits en anglais, dans `doc/en`.

### Diffusion à l'antenne

- La priorité « imprévu » (breaking), au-dessus des spéciaux ([#402](https://github.com/dascritch/machincast/issues/402)), et ce que fait un événement à la fin de sa liste ([#350](https://github.com/dascritch/machincast/issues/350)).
- Revenir au début du sonore, ou recommencer l'événement, depuis le menu Diffusion ([#366](https://github.com/dascritch/machincast/issues/366)) ; couper l'antenne depuis le prochain sonore, par le secours ou par un feed ([#323](https://github.com/dascritch/machincast/issues/323)).
- Un secours qui fait appel à un flux externe est signalé ([#403](https://github.com/dascritch/machincast/issues/403)) ; la mémoire tampon d'un feed se règle, et l'onglet Antenne montre son remplissage ([#351](https://github.com/dascritch/machincast/issues/351)).
- L'antenne reprend après la disparition de sa sortie audio ([#237](https://github.com/dascritch/machincast/issues/237)) ; une sortie factice se joue sur une carte virtuelle, que le VU-mètre écoute ([#400](https://github.com/dascritch/machincast/issues/400)).
- Les banques dans l'ordre du nom de fichier de leurs sonores, de A à Z ou de Z à A ([#454](https://github.com/dascritch/machincast/issues/454)).
- Une émission peut prêter son nom au fil musical jusqu'à son heure de fin, liste vide comprise, quand l'équipe ne peut pas prendre l'antenne à l'heure ([#399](https://github.com/dascritch/machincast/issues/399)).

### Interface

- L'onglet Antenne, avec le témoin du service et de la diffusion, et les emoji de ses actions ([#322](https://github.com/dascritch/machincast/issues/322), [#344](https://github.com/dascritch/machincast/issues/344)).
- Les onglets retenus d'un lancement à l'autre ([#321](https://github.com/dascritch/machincast/issues/321)), déplaçables ([#405](https://github.com/dascritch/machincast/issues/405)), au titre limité à 40 caractères ([#398](https://github.com/dascritch/machincast/issues/398)), et de nouveaux raccourcis : Ctrl+W, Ctrl+S, Ctrl+Entrée, Ctrl+Maj+T ([#428](https://github.com/dascritch/machincast/issues/428)).
- La pré-écoute dans une fenêtre indépendante ([#325](https://github.com/dascritch/machincast/issues/325)), et le calendrier en liste du jour ou de la semaine, avec le zoom des heures ([#326](https://github.com/dascritch/machincast/issues/326)).
- Les listes et tableaux : colonne d'anomalie à gauche ([#327](https://github.com/dascritch/machincast/issues/327)), export en CSV ([#329](https://github.com/dascritch/machincast/issues/329)), filtre plein texte ([#393](https://github.com/dascritch/machincast/issues/393)), lignes alternées ([#412](https://github.com/dascritch/machincast/issues/412)), et lecture par pages des longues listes ([#383](https://github.com/dascritch/machincast/issues/383)).
- Les fiches : liste vide en avertissement, masquage plus explicite ([#328](https://github.com/dascritch/machincast/issues/328)), grisées pendant l'enregistrement et fermées quand il réussit ([#382](https://github.com/dascritch/machincast/issues/382)).
- La fiche d'un sonore : début et fin réglables sur la frise ([#330](https://github.com/dascritch/machincast/issues/330)), relations à retirer ([#331](https://github.com/dascritch/machincast/issues/331)), et l'analyse complète proposée, avec le retour aux valeurs du fichier ([#388](https://github.com/dascritch/machincast/issues/388)).
- Les préférences de l'interface et les paramètres du service, séparés selon ce qui redémarre la diffusion ([#389](https://github.com/dascritch/machincast/issues/389)) ; le seuil de silence à la page Crossfades ([#324](https://github.com/dascritch/machincast/issues/324)) ; le choix des cartes son au lancement ([#339](https://github.com/dascritch/machincast/issues/339)).
- Le statut des indexations de sonores ([#392](https://github.com/dascritch/machincast/issues/392)), et la fenêtre de version, avec ses liens ([#332](https://github.com/dascritch/machincast/issues/332)).
- Aide → « Votre installation », le document éditable de l'équipe, et le lien de l'équipe ([#451](https://github.com/dascritch/machincast/issues/451)).
- Plus réactive : le VU-mètre se met en pause pendant la veille de la session, et les attentes ne figent plus la fenêtre ([#346](https://github.com/dascritch/machincast/issues/346), [#387](https://github.com/dascritch/machincast/issues/387), [#345](https://github.com/dascritch/machincast/issues/345), [#343](https://github.com/dascritch/machincast/issues/343)) ; plus stable ([#413](https://github.com/dascritch/machincast/issues/413), [#320](https://github.com/dascritch/machincast/issues/320)).

### Sauvegarde et reprise

- `Machin backup-db` exporte la base, aussi depuis Maintenance → Exporter la base… ; sur un poste neuf, `install.sh` propose de la réimporter ; la page Sauvegarde des paramètres du service copie aussi `machincast.toml` ([#347](https://github.com/dascritch/machincast/issues/347)).

### Installation et administration

- Les minuteurs du service : l'indexation rapide toutes les heures, et chaque jour, à l'heure réglée, la purge puis l'audit complet ([#455](https://github.com/dascritch/machincast/issues/455)).
- Le poste d'antenne ne s'éteint, ne redémarre ni ne se met en veille sans le mot de passe d'un administrateur ([#448](https://github.com/dascritch/machincast/issues/448)).
- `Machin grant-read` fait lire les sonores au service ; la désinstallation ne retire jamais un répertoire qui contient des sonores ([#381](https://github.com/dascritch/machincast/issues/381), [#430](https://github.com/dascritch/machincast/issues/430)).
- `Machin logs` suit le journal du service ([#459](https://github.com/dascritch/machincast/issues/459)) ; les démarrages et arrêts des programmes sont notés ([#341](https://github.com/dascritch/machincast/issues/341)) ; un plantage laisse un rapport ([#342](https://github.com/dascritch/machincast/issues/342)).
- Le verrou de l'indexation par mode : rapide et complète peuvent tourner ensemble ([#401](https://github.com/dascritch/machincast/issues/401)).

### Documentation et qualité

- La documentation relue d'un bout à l'autre ([#461](https://github.com/dascritch/machincast/issues/461)), précisée ([#338](https://github.com/dascritch/machincast/issues/338)), le document d'architecture arc42 ([#446](https://github.com/dascritch/machincast/issues/446)), et le guide de contribution renommé `CONTRIBUTING.md` ([#456](https://github.com/dascritch/machincast/issues/456)).
- La qualité du code : dépendances verrouillées, fonctions et classes découpées, requêtes regroupées, tests plus robustes ([#340](https://github.com/dascritch/machincast/issues/340), [#390](https://github.com/dascritch/machincast/issues/390), [#437](https://github.com/dascritch/machincast/issues/437), [#438](https://github.com/dascritch/machincast/issues/438), [#439](https://github.com/dascritch/machincast/issues/439), [#440](https://github.com/dascritch/machincast/issues/440), [#441](https://github.com/dascritch/machincast/issues/441), [#442](https://github.com/dascritch/machincast/issues/442), [#443](https://github.com/dascritch/machincast/issues/443), [#444](https://github.com/dascritch/machincast/issues/444), [#445](https://github.com/dascritch/machincast/issues/445), [#384](https://github.com/dascritch/machincast/issues/384), [#470](https://github.com/dascritch/machincast/issues/470)) ; des tests ciblés par ticket ([#408](https://github.com/dascritch/machincast/issues/408)) et le flux des branches `preprod`, `qualif`, `main` ([#480](https://github.com/dascritch/machincast/issues/480)).

### Merci

À Xavier Mouton-Dubosc ([dascritch](https://github.com/dascritch)), *broadcasting manager* de [Radio &lt;FMR&gt; 89.1 Toulouse](https://radio-fmr.net), qui a demandé chacune de ces améliorations, signalé chaque problème et relu chaque changement.

## 0.9.0 — 2026-10-28

Première version publiée, avant la 1.0 : tout ce que fait MachinCast, fonctionnalité par fonctionnalité.

### Diffusion à l'antenne : Machin player

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

À Xavier Mouton-Dubosc ([dascritch](https://github.com/dascritch)), *broadcasting manager* de [Radio &lt;FMR&gt; 89.1 Toulouse](https://radio-fmr.net), qui a demandé chacune de ces fonctionnalités, signalé chaque problème et relu chaque changement.
