Tu es un développeur d'application pour Linux, tu dois développer un projet comportant des binaires shell et une application avec une interface graphique Qt.

# Architecture

Le projet "Machincast" est un système automatisé de diffusion sonore à partir de plusieurs banques de sonores et d'événements. Son usage est de fournir un fil antenne diffusable pour une radio en dehors de ses émissions en direct.

Le système doit fonctionner dans l'environnement Linux.

Tous les binaires exécutables générés commencent par le nom "Machin\_",   
Tous les binaires sans interface graphique doivent ne pouvoir être lancés que via un wrapper bash appelé "Machin".

Toute la conception logicielle doit être faite en TDD, avec des tests en BDD. Chaque nouvelle fonctionnalité doit donc avoir un test associé et un commit git. Chaque commit git est lié à un ticket.  
Tout le projet doit avoir une documentation générée en markdown dans le répertoire \`/doc\` du projet

## Base de données

La base de donnée est en postgresql, et est accédée par les exécutables en socket unix local.  
Une deuxième base de donnée avec la même structure de données est créée à des fins de tests, notamment pour la conception en TDD.

La base de données a les tables suivantes  :

- Sonores (fichiers ou stream) avec leurs emplacements et leurs métadonnées (artistes, titre, année, temps de crossfade au début, temps de crossfade à la fin, nombre maximum de lectures, actif)   . L'emplacement disque est une clé unique  
- Log de passage du sonore, avec  
  - heure de début,  
  - heure de fin,  
  - si la lecture a eu lieue sans incident  
- Banque , avec  
  - nom de banque  
  - métadonnées remplaçant les informations publiques  d'artiste et de titre  
  - répertoire de fichiers  
  - si le fichier est choisi au hasard ou par ordre d'entrée  
  - liste des sonores qui en font partie (one-to-many).  
- Événement horaire,   
  - date et heure de début d'événement  
  - date et heure de fin d'événement  
  - priorité (fil musical , émission , spécial)  
  - récurrence de l'événement,  
  - métadonnées (artiste, titre)  
  - Liste à lire de banques et/ou sonores 

## Wrapper shell 

Ce wrapper sert à appeler les binaires.   
Il prend en paramètre le nom du binaire à appeler et les options à lui transmettre.

Dans les options génériques, il propose :

- L'autocomplétion  
- l'aide minimale en ligne  
- une aide complète en ligne

Il peut proposer de lire en direct les logs du binaire lecture 

## Binaire lecture

Le système fonctionne avec un binaire simple qui ne fait que lire les événements et les jouer. 

Ce binaire se base sur un fichier de configuration lu à son lancement.

Ce binaire a les droits suivants sur la table Psql :

- Sonores : lecture   
- Événement : lecture  
- Banque : lecture  
- Log : écriture

Le binaire lit un événement par défaut de priorité "fil musical", qui doit toujours exister en base.

Il interrompt si un événement en base a lieu à cet horaire sur une priorité supérieure et bascule sur cet événement et joue sa liste de lecture, constituée de sonores et de banques. S'il s'agit d'une banque, il prend un seul sonore de cette banque.

Si la liste de lecture de l'événement est terminée mais qu'on n'est pas encore à l'heure de fin de l'événement, il boucle au début des éléments à jouer dans l'événement

Ce binaire a des modules de sortie, notamment :

- un log stdout (privé) qui indique les morceaux lancés, aka airplay  
- un log stderr (privé) qui indique incident et crashes  
- un csv (privé) de l'airplay  
- un document .pls playlist (privé) de fichier  
- un html (public) de l'airplay

Si le module de sortie est "privé", il indique TOUS les tracks envoyés. S'il est "public", les tracks sont envoyés si indiqués dans le paramètre de la playlist

Sur option de lancement, le binaire peut simuler ce qu'il ferait entre une certaine heure et une autre heure, et en n'exportant que des documents .csv , .pls et .html dans un nommage à part, et dans ce mode de simulation, il n'a pas le droit d'écrire une seule entrée dans la base de donnée, et n'utilise pas de sortie sonore.

## Binaire indexation

Analyse chaque entrée en Sonore (sauf streaming) :

- vérifie le format   
- vérifie s'il est lisible  
- si un problème, le signale en STDERR et marque le sonore en "inactf"

Analyse chaque fichier audio (type mp3, mp4, ogg, flac, wav, aiff)  dans le répertoire associé à une banque, s'il n'est pas encore indexé dans la table "Sonores"

## Interface graphique

L'interface est construite avec le toolkit Qt .

Il présente plusieurs écrans.

### Écran par défaut

- Indique l'heure actuelle  
- Indique si le binaire lecture est en cours de fonctionnement   
- Indique l'airplay sur les 12 dernières heures sous forme de table  
- Met en avant le sonore en cours de lecture, son heure de début, sa durée totale, son heure de fin estimée, la barre de progression en lecture  
- Et juste accolé le prochain sonore qui sera diffusé, avec heures de début et fin estimés, durée totale et s'il semble sain.  
- Un VU-Mètre et un bargraph de la sortie sonore actuelle

### Écran de détails d'un sonore

- Propose d'éditer le nom du morceau et d'artiste  
- Permet une lecture en pré-écoute avec un programme de lecture externe  
- Donne une table des dernières heures de passage et si un incident en lecture a eu lieu

### Écran de détails d'une banque

- Propose d'éditer le nom interne de la banque  
- Propose de ne pas envoyer les noms d'artistes et de morceau de cette banque  
- Propose de choisir séquentielement dans la banque le sonore ou au hasard  
- éditer une liste de sonores liés à cette banque

### Écran de détails d'un événement

- Propose d'éditer le nom interne de l'événement  
- Propose d'écrire le nom public de l'événement  
- La priorité de l'événement (fil musical, émission , spécial)  
- Propose de ne pas envoyer les noms d'artistes et de morceau durant cet événement  
- la date et l'heure de début de l'événement  
- la date et l'heure de fin de l'événement  
- la récurrence de l'événement (pas de récurrence / tous les jours / un jour particulier de la semaine)  
- éditer une liste de playlists et/ou de sonores à lire lors de l'événement

### Écran des incidents

Montre sous forme de table les logs des incidents, avec par incident :

-  horaire de l'incident,  
- lien vers l'écran du sonore,   
- lien vers l'écran de la playlist  
- lien vers l'écran de l'événement si précisé.

### Écran de simulation

L'utilisateur entre une date et heure de début et une date et heure de fin, le logiciel lance le binaire de lecture en mode simulation et  présente un tableau des sonores qui seraient joués. Ce tableau peut être exportés en mode .pls ; csv et .html.

### Menu de l'application

Le menu propose 

- ajouter un sonore  
- ajouter une playlist  
- ajouter un événement  
- de lancer/arrêter  le binaire de lecture  
- de lancer une ré-indexation générale de toutes les banques  
- de choisir une sortie audio spécifique pour les pré-écoutes
