# Le station ID régulier

La station doit dire son nom régulièrement, environ tous les quarts d'heure ; mais les morceaux durent de 2 à 13 minutes, et un station ID placé dans la liste du fil musical passe tantôt après 12 minutes, tantôt après 22 ([#460](https://github.com/dascritch/machincast/issues/460)).
Le plugin « Station ID régulier » fait passer un station ID au bon moment, entre deux morceaux, à l'antenne comme dans les sonores à venir de l'onglet Antenne et dans la simulation.

## Le régler

Ses réglages sont dans `machincast.toml`, section `[plugins.timely_station_id]` : la banque des station ID à jouer, les banques à surveiller, l'écart minimal et maximal entre deux station ID, en minutes, et le placement ; le [README du plugin](../README.md) les détaille.

- Un passage d'une banque surveillée, par exemple un jingle saisonnier qui dit le nom de la station, compte comme un station ID.
- Placement `before` : le station ID passe avant le morceau qui ferait dépasser le maximum, dès que le minimum est passé.
- Placement `after` : il passe au premier changement de morceau après le maximum ; aucun morceau n'est avancé, mais l'écart dépasse le maximum.

Un morceau plus long que le maximum passe juste après un station ID : rien ne le coupe.
Le premier station ID passe dès le premier morceau, si aucun n'est connu.

## Choisir les événements

Dans la fiche d'un événement, cocher **Station ID régulier**, sous **Secours d'un stream tombé**, puis enregistrer.
L'infobulle de la case rappelle la banque et l'écart réglés.
Seule la liste de l'événement coché reçoit des station ID ; ni la suite d'une séquence, ni un sonore inséré à la main, ni le stream d'un feed n'en reçoivent avant eux.
