# Les émissions en alternance

Certaines émissions se partagent le même créneau horaire selon la semaine du mois : par exemple, le mercredi de 20 h à 21 h, « Sonia » le premier mercredi, « Les ahuris » le deuxième et le quatrième, « Zôtre » le troisième ([#609](https://github.com/dascritch/machincast/issues/609)).
D'autres alternent simplement une semaine sur deux, par quinzaine, une semaine sur trois ou une semaine sur quatre.
Le plugin « Émissions en alternance » fait jouer chaque semaine la bonne émission, et la montre sous son nom, partout : à l'antenne, dans le calendrier de l'interface et de l'intranet, et dans l'affichage public.

## Préparer les émissions

Chaque émission a sa fiche d'événement, une émission ou un spécial, avec sa liste de lecture, son nom public, sa fin de liste et ses secours, comme toute émission.
Leurs dates ne comptent plus dès qu'elles sont choisies pour une alternance : elles ne jouent alors que sur le créneau de l'événement méta.

## L'événement méta

1. Créer l'événement du créneau, par exemple « Mercredi soir », une émission le mercredi de 20 h à 21 h, et l'enregistrer.
2. Dans sa fiche, cocher **Émissions en alternance**, sous les jours de la récurrence : la liste de lecture disparaît, remplacée par la section du plugin.
	La case ne se coche qu'une fois un jour de la semaine coché : les émissions alternent les jours de la récurrence ; sans jour, une alternance déjà cochée peut se décocher, mais ne s'enregistre pas.
3. Cocher, dans **Émissions qui se partagent le créneau**, celles qui alternent.
	Une émission qui n'existe pas encore se crée de là, par **Créer une émission sur ce créneau partagé**, à côté : son nom demandé, elle s'ajoute à la liste, « Clara (à créer) », cochée.
	Elle n'est créée qu'à l'enregistrement de l'événement méta, sur son créneau, sans jour de récurrence : il reste à remplir sa liste de lecture dans sa propre fiche.
	Son nom est aussi son nom public ; elle reprend de la fiche de l'événement méta, telle qu'elle est enregistrée, **Artiste et titre**, la **Fin de liste** et son secours, et le **Secours de stream tombé**.
	Un nom déjà pris par un autre événement est refusé.
4. Choisir le **Rythme** :
	- **Par mois, selon la semaine du mois** : la **Rotation** a cinq lignes, « 1er mercredi du mois », « 2e mercredi du mois », jusqu'au « 5e mercredi du mois », qui ne revient que certains mois ;
	- **Par quinzaine, une semaine sur deux** : la **Rotation** a deux lignes, « 1re semaine de la quinzaine » et « 2e semaine de la quinzaine », chacune avec son prochain passage, « dont le 16/12/2026 » ; la quinzaine part de la semaine de la première occurrence de l'événement, et continue d'un mois à l'autre, sans recommencer au 1er ;
	- **Une semaine sur trois** et **Une semaine sur quatre** : de même, la **Rotation** a trois ou quatre lignes, « 1re semaine sur 3, dont le 23/12/2026 »…
5. Choisir, dans la **Rotation**, l'émission de chaque ligne. « — l'événement lui-même » laisse l'événement méta jouer sa propre liste ce jour-là.
6. Changer, au besoin, un des **Passages à venir** : chacun suit la rotation, « Selon la rotation : Sonia », ou une émission choisie pour ce jour-là seulement, par exemple pour un échange entre deux équipes.
7. Enregistrer.

Un événement qui revient plusieurs jours par semaine parle de « 1re semaine du mois » plutôt que de « 1er mercredi ».
Décocher **Émissions en alternance**, puis enregistrer, retire l'alternance : l'événement retrouve sa liste, et les émissions leurs propres dates.

## La fiche d'une émission de l'alternance

Dans la fiche d'une émission qu'une alternance fait jouer, l'encadré « Grille : première occurrence, et jours où elle revient » laisse la place à l'encadré **Créneau partagé**, puisque ses propres dates ne comptent plus.
Il dit le créneau : « Cette émission partage le créneau « Mercredi soir », le mercredi de 20h à 21h. »
Dessous, un tableau donne les émissions du créneau, par prochain passage, celle de la fiche en gras : la **Rotation** qui les fait jouer (« 1er et 5e mercredi du mois », « Choisie à la main », « Hors de la rotation »), leur **Prochain passage**, et leur nom.
Un double clic sur la ligne d'une autre émission ouvre sa fiche.
Retirée de l'alternance, elle retrouve l'encadré de sa grille.
