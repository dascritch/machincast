# Le cartouchier

Le cartouchier est une page de Machin intranet, « Cartouchier » dans le bandeau, faite pour un écran tactile au studio ([#512](https://github.com/dascritch/machincast/issues/512)).

## Ce que montre la page

En haut, l'antenne en direct, comme l'accueil de l'intranet : l'heure, le texte public, l'événement en cours (début, fin, temps restant) et le suivant (début, fin), le sonore en cours (durée, temps restant) et le prochain (durée, temps avant son début).
Les décomptes s'affichent à la seconde, calculés au centième ; la page se relit toute seule.

En dessous, les boutons du compte connecté, larges, chacun de sa couleur.
Un bouton grisé ne peut pas servir maintenant ; son infobulle dit pourquoi :

- il insère un sonore d'une banque marquée « ne pas répéter », et le sonore à l'antenne vient d'elle ;
- ce qu'il vise, une séquence, une banque ou un secours, est supprimé.

Un compte « consulter » voit l'antenne, et ses boutons grisés : seul un compte « actions API » appuie.

## Appuyer

Chaque bouton demande une action à Machin player, au nom du compte connecté, et la ligne sous les boutons dit la réponse : ✓ faite, ou ✗ refusée, avec sa raison (par exemple « aucune séquence à l'antenne »).
Le log de MachinCast consigne chaque action avec le compte et son origine, l'intranet ; l'onglet Incidents les montre.

Les actions possibles sont celles du menu « Diffusion » de l'interface, sauf démarrer et arrêter la diffusion :

| Action | Ce qu'elle fait |
| --- | --- |
| Sauter au sonore suivant | Le sonore en cours s'éteint, le prochain sonore démarre. |
| Sauter après la séquence | La séquence en cours s'arrête, la suite de la liste reprend. |
| Couper l'événement par le fil musical | L'émission en cours s'arrête, le fil musical reprend l'antenne. |
| Revenir au début du sonore, Recommencer l'événement, Recommencer la séquence | Rejoue depuis le début. |
| Avancer l'événement suivant | L'événement suivant commence aussitôt, jusqu'à sa fin prévue. |
| Couper l'antenne par un secours, par un feed | Le secours, ou le stream du feed, tient l'antenne jusqu'à la fin prévue de l'émission coupée. |
| Insérer une séquence, un sonore d'une banque après ce sonore | Passe après le sonore en cours, avec, si le bouton le règle, un blanc de 5 secondes avant, après, ou les deux. |

## Régler les boutons

Dans Machin interface, menu « Plugins », « Cartouchier… » : choisir le compte, puis, pour chaque bouton, son intitulé, sa couleur (`#rrggbb`), son action, ce qu'elle vise (une séquence, une banque, un secours ou un feed) et, pour une insertion, son blanc.
« Ajouter » le met au bout, « Remplacer » change le bouton choisi, « Monter » et « Descendre » le déplacent, « Retirer » l'enlève.
Chaque changement s'enregistre aussitôt ; la page du cartouchier le montre à son prochain chargement.

Par exemple, l'émission « Infos » aura « Couper l'antenne » par le secours, et des insertions de la banque « Identifiant station court », de la séquence « Partenariats » et de la séquence « Chronique info » ; l'émission « Les gaufres électriques » aura des insertions des banques « Identifiant station court », « Identifiant station long » et « Musiques jazz ».
