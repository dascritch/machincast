# Les couleurs des émissions

Le plugin « Couleurs des émissions » colore chaque émission selon son genre, talk, jazz, metal, reggae…, dans le calendrier de l'interface, dans celui de l'intranet, et dans les tableaux d'airplay, par un trait épais à gauche de la cellule de l'événement ([#628](https://github.com/dascritch/machincast/issues/628)).
Un événement sans genre prend la couleur de sa priorité : gris pour le fil antenne, vert pour les émissions, rouge pour les spéciales.
Le nom d'un bloc passe du noir au blanc quand sa couleur est sombre, pour rester lisible.

## Donner un genre à une émission

1. Ouvrir la fiche de l'événement.
2. Choisir son **Genre**, sous **Secours d'un stream tombé** : « aucun genre », ou l'un des genres, chacun avec un carré de sa couleur.
3. Enregistrer : le calendrier prend la couleur aussitôt.

Un événement a un genre au plus.

## Régler les genres et les couleurs

Menu **Plugins**, **Couleurs des émissions** :

- le tableau des **Genres** : chaque nom, à écrire dans sa cellule, et sa couleur, à choisir dans le sélecteur de couleur, qu'ouvre un clic sur sa cellule, ou Entrée ou Espace ;
- **Ajouter** crée la ligne « nouveau genre », à renommer ; **Retirer** enlève la ligne choisie ;
- **Couleurs des événements sans genre** : celle du fil antenne, des émissions et des spéciales ;
- **Enregistrer** écrit le tout.

Un nom vide ou déjà pris, même avec d'autres majuscules, est refusé : le message le dit, et rien n'est écrit.
Un genre retiré quitte les événements qui l'avaient : ils reprennent la couleur de leur priorité.

Machin intranet relit les couleurs au plus toutes les 30 secondes.
