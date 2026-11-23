# Les émissions en alternance

Certaines émissions se partagent le même créneau horaire selon la semaine du mois : par exemple, le mercredi de 20 h à 21 h, « Sonia » le premier mercredi, « Les ahuris » le deuxième et le quatrième, « Zôtre » le troisième ([#609](https://github.com/dascritch/machincast/issues/609)).
Le plugin « Émissions en alternance » fait jouer chaque semaine la bonne émission, et la montre sous son nom, partout : à l'antenne, dans le calendrier de l'interface et de l'intranet, et dans l'affichage public.

## Préparer les émissions

Chaque émission a sa fiche d'événement, une émission ou un spécial, avec sa liste de lecture, son nom public, sa fin de liste et ses secours, comme toute émission.
Leurs dates ne comptent plus dès qu'elles sont choisies pour une alternance : elles ne jouent alors que sur le créneau de l'événement méta.

## L'événement méta

1. Créer l'événement du créneau, par exemple « Mercredi soir », une émission le mercredi de 20 h à 21 h, et l'enregistrer.
2. Dans sa fiche, cocher **Émissions en alternance** : la liste de lecture disparaît, remplacée par la section du plugin.
3. Cocher, dans **Émissions qui se partagent le créneau**, celles qui alternent.
4. Choisir, dans **Rotation dans le mois**, l'émission de chaque semaine : « 1er mercredi du mois », « 2e mercredi du mois », jusqu'au « 5e mercredi du mois », qui ne revient que certains mois. « — l'événement lui-même » laisse l'événement méta jouer sa propre liste ce jour-là.
5. Changer, au besoin, un des **Passages à venir** : chacun suit la rotation, « Selon la rotation : Sonia », ou une émission choisie pour ce jour-là seulement, par exemple pour un échange entre deux équipes.
6. Enregistrer.

Un événement qui revient plusieurs jours par semaine parle de « 1re semaine du mois » plutôt que de « 1er mercredi ».
Décocher **Émissions en alternance**, puis enregistrer, retire l'alternance : l'événement retrouve sa liste, et les émissions leurs propres dates.
