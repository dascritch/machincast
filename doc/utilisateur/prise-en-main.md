# Prendre en main l'interface

[Guide de l'antenne](README.md) › Prendre en main l'interface

- [La fenêtre](#la-fenêtre)
- [Pour bien démarrer](#pour-bien-démarrer)
- [Accueil](#accueil)
- [Passer d'un onglet à l'autre](#passer-dun-onglet-à-lautre)
- [Menus](#menus)
- [Rafraîchir les onglets](#rafraîchir-les-onglets)
- [Rechercher](#rechercher)
- [Préférences](#préférences)
- [Textes saisis](#textes-saisis)

## La fenêtre

**Pour l'ouvrir**, choisir **MachinCast** dans le menu des applications, rubrique Multimédia, ou double-cliquer sur son icône, le panneau orange au casque des équipes techniques, sur le bureau quand l'installation l'y a déposée. Aucun terminal n'est nécessaire.

<img src="../../src/machincast/interface/machincast.png" width="64" height="64" alt="Icône de MachinCast : un panneau de chantier orange en losange, avec un casque audio noir et les lettres AMR">

**Machin interface** s'ouvre sur une fenêtre à onglets, un par écran. Au lancement : **Accueil**, **Événements**, **Séquences**, **Banques** et **Incidents**. Les listes des **Sonores** et des **Marques-pages**, et le **Calendrier**, s'ouvrent à la demande, par le menu **Affichage** : « Ouvrir l'onglet Sonores », « Ouvrir l'onglet Marques-pages » et « Ouvrir l'onglet Grille horaire ». Les Sonores et les Marques-pages se placent après les Banques ; un onglet déjà ouvert revient au premier plan. Les onglets ouverts à la demande, et ceux des fiches, se ferment par leur croix ; une liste fermée puis rouverte retrouve son filtre et son tri.

**Icônes** : une même icône désigne partout un même genre, dans les onglets, le menu **Affichage**, la recherche, les relations d'un sonore et les boutons **Fiche…** de l'accueil ([#215](https://github.com/dascritch/machincast/issues/215)). Elles prennent la couleur du texte, en thème clair comme en thème sombre.

| Icône | Genre |
| --- | --- |
| une croche | Sonore |
| une feuille et sa liste à puces | Séquence |
| un dossier | Banque |
| une montre | Événement |
| un calendrier | Grille horaire (onglet « Calendrier ») |
| une boule de divination | Simulation |

**Sans base de données**, l'interface ne peut rien montrer : une fenêtre d'erreur, « MachinCast : base de données injoignable », l'explique, et son bouton « Ouvrir INSTALL.md » mène à la section [En cas de problème](../../INSTALL.md#en-cas-de-problème), pour l'administrateur du poste.

## Pour bien démarrer

Au lancement, l'interface cherche ce qui manque pour que l'antenne puisse tourner :

- un **fil musical**, l'événement qui tient l'antenne quand aucun autre ne la prend ;
- les banques **Identifiant station**, **Musique rotation lourde**, **Musique rotation normale**, **Musique rotation rare** et **Musique rotation de nuit**, reconnues à leur nom, sans tenir compte des majuscules ;
- sur une vraie sortie audio, le **périphérique de l'antenne**, sans lequel la diffusion ne démarre pas.

![La fenêtre « Pour bien démarrer », qui propose de créer le fil musical et les banques qui manquent](../captures/pour-bien-demarrer.png)

S'il en manque, la fenêtre **Pour bien démarrer** les propose, chacun coché :

- **Créer** crée ce qui est coché. Le fil musical est permanent. Les banques sont aléatoires et vides : elles se remplissent depuis leur [fiche](sonores.md#fiche-dune-banque), ou par l'indexation de leurs répertoires. « Identifiant station » est marquée « ne pas répéter ». Un fil musical encore vide reçoit une rotation type : Identifiant station, rotation lourde, normale, lourde, rare. La rotation de nuit reste à placer dans un événement de nuit. La barre d'état dit ce qui a été créé.
- Le **périphérique de l'antenne** se choisit parmi ceux du poste, sauf celui de la pré-écoute. La diffusion le prend à son prochain démarrage (**Diffusion → Redémarrer la diffusion**).
- **Plus tard** ne crée rien : la fenêtre revient au lancement suivant.
- **Ne plus proposer au lancement** éteint la fenêtre ; elle se rallume dans les [préférences](#préférences). Sans elle, l'interface recrée au lancement un fil musical vide s'il n'en existe aucun, et le dit dans la barre d'état.

Après la suppression ou l'enregistrement d'un événement, l'interface recrée toujours un fil musical s'il n'en reste aucun.

## Accueil

L'onglet **Accueil** montre en un coup d'œil ce qui passe et ce qui va passer.

![L'accueil : l'heure, le texte public, l'état de la diffusion, l'événement à l'antenne, le sonore en cours et le prochain, le VU-mètre et l'historique](../captures/accueil.png)

- **En haut** : l'heure du poste, à la seconde (la date est dans son infobulle) ; le **texte public** du sonore en cours, tel que l'affiche la page publique de la radio (`—` sans texte, par exemple pour un sonore masqué) ; et l'état de la diffusion : `En diffusion`, `En silence` (rien à diffuser) ou `À l'arrêt`.
- **Événement à l'antenne** : son nom et ses heures, « de 20:00 à 22:00 », « depuis 19:00 » pour une occurrence sans fin, ou « permanent » pour un fil musical.
- **Sonore en cours**, à gauche : l'artiste et le titre, l'événement qui le joue, la séquence et la banque d'où il vient (`—` s'il n'en vient pas), l'horaire (début, fin prévue et durée, « 20:00:00 – 20:03:34 (3:34) »), l'emplacement du fichier ou l'adresse du stream. Pour un fichier, sa **frise** ([#230](https://github.com/dascritch/machincast/issues/230)) : la forme d'onde, ses blancs hachurés et ses fondus, tels que l'antenne les joue, règles de sa banque comprises, et la tête de lecture ; dessous, le temps qui reste, « reste 3:05 ». C'est la frise de la [pré-écoute](sonores.md#frise-dun-fichier), qui ne fait ici que se regarder : un clic n'y déplace rien. Un stream a, à la place, une barre qui dit le temps qui reste, s'il est connu.
- **Prochain sonore**, à droite : les mêmes informations, avec l'horaire prévu et, pour un fichier, sa frise sans tête de lecture, et **Sain** : `oui` si son fichier est présent, actif, lisible, et que sa dernière lecture s'est passée sans incident ; `non` sinon. Le prochain sonore annoncé est bien celui qui passera, même tiré au hasard : il ne change que si un événement coupe la diffusion, si son événement est fini, ou s'il est désactivé ou expiré entre-temps.
- **Coupure annoncée** : quand un événement commencera pendant le sonore en cours, il le coupera net. L'horaire finit alors à la coupure et nomme l'événement, « 20:00:00 – 20:02:00 (coupé par « Journal », sur 3:34) », le temps qui reste dit « reste 1:30 avant « Journal » », et le prochain sonore est celui que jouera cet événement.
- **Stream** : son horaire est « 20:00:00, durée inconnue », et il n'est pas testé à l'avance : `non testé`.
- **Emplacement** : un long chemin ne déborde pas ; sa fin reste visible, il se sélectionne et se copie, et son infobulle le donne en entier.
- **Boutons Fiche…** : à droite du titre, de l'événement, de la séquence et de la banque, ils ouvrent la fiche de l'élément.
- **Airplay des 12 dernières heures** : les passages, du plus récent au plus ancien, avec le début, la fin (`en cours` pour le sonore à l'antenne), la durée, l'artiste, le titre, l'événement, la séquence, la banque, et `oui` dans la colonne « Incident » pour un passage qui en a eu un. Un double-clic sur une ligne ouvre la fiche du sonore, de l'événement, de la séquence ou de la banque cliqué ; un clic droit propose la [pré-écoute](sonores.md#pré-écoute) du sonore. L'interface est réservée à l'équipe : l'artiste et le titre y sont toujours affichés, même masqués sur la page publique.

L'accueil suit la diffusion en direct. Quand elle s'arrête, il affiche `À l'arrêt`, et la retrouve tout seul dès qu'elle reprend. Il doit tourner sur le poste de la diffusion, avec le même compte : sinon il ne la voit pas.

### VU-mètre de l'antenne

Entre les deux sonores, la colonne **Antenne** montre ce qui sort réellement à l'antenne :

- **Saturation**, au-dessus : ce voyant s'allume, rouge, dès qu'une crête atteint -1 dB, et le reste 3 secondes. Il se cache dans les [préférences](#préférences).
- **VU-mètre** : une barre par canal, « G » et « D », de -60 dB en bas à 0 dB en haut, séparées par l'échelle. La partie pleine est le niveau moyen ; la partie plus claire au-dessus, la crête du moment ; un trait garde la plus haute crête pendant 2 secondes. Vert, orange au-delà de -12 dB, rouge au-delà de -3 dB.
- **Silence**, en dessous : ce voyant s'allume, orange, quand le son reste à -50 dB ou moins pendant 5 secondes : un blanc d'antenne. Il s'éteint dès que le son revient.
- **Écouter l'antenne** : un clic sur le VU-mètre ouvre la [pré-écoute](sonores.md#pré-écoute) sur l'antenne, sans la lancer.

Le VU-mètre écoute le périphérique de l'antenne, quel que soit le programme qui y joue. Quand il ne peut pas, un message le dit sous les voyants :

| Message | Ce qu'il faut faire |
| --- | --- |
| `Indisponible avec la sortie ALSA, qui n'a pas de port de monitoring.` | Rien : le poste utilise une sortie qui ne permet pas d'écouter l'antenne. L'administrateur peut passer à PipeWire ou PulseAudio. |
| `Indisponible : périphérique de l'antenne à renseigner.` | Choisir le périphérique de l'antenne dans **Fichier → Préférences…**, page **Audio**. |
| `Indisponible :` suivi d'une erreur | Le périphérique est débranché, ou le son du poste ne répond pas. Le VU-mètre réessaie toutes les 5 secondes. |

## Passer d'un onglet à l'autre

Les 12 premiers onglets s'ouvrent au clavier, par <kbd>Maj</kbd>+<kbd>F1</kbd> à <kbd>Maj</kbd>+<kbd>F12</kbd>, selon leur rang : <kbd>Maj</kbd>+<kbd>F1</kbd> est toujours l'Accueil ; au lancement, <kbd>Maj</kbd>+<kbd>F2</kbd> à <kbd>Maj</kbd>+<kbd>F4</kbd> mènent aux Événements, Séquences et Banques, <kbd>Maj</kbd>+<kbd>F5</kbd> aux Incidents, puis aux fiches et aux autres onglets, dans l'ordre où ils sont ouverts. Ouvrir ou fermer un onglet décale ceux qui le suivent. L'infobulle de chaque onglet donne son raccourci.

## Menus

Une fonction pas encore écrite a déjà son entrée, grisée : son infobulle donne le ticket qui l'apportera.

| Menu | Entrée | Rôle |
| --- | --- | --- |
| Fichier | Préférences… | Les réglages de l'interface et de l'audio ([Préférences](#préférences)). |
| Fichier | Quitter | Ferme l'interface, aussi par <kbd>Alt</kbd>+<kbd>Q</kbd>. Demande d'abord quoi faire des fiches modifiées. La diffusion, elle, continue. |
| Affichage | Rafraîchir les onglets | Relit ce que d'autres postes, l'indexation ou la diffusion ont changé, aussi par <kbd>F5</kbd> ([Rafraîchir les onglets](#rafraîchir-les-onglets)). |
| Affichage | Rechercher… | Ouvre la recherche, aussi par <kbd>Ctrl</kbd>+<kbd>F</kbd> ([Rechercher](#rechercher)). |
| Affichage | Ouvrir l'onglet Sonores, Ouvrir l'onglet Marques-pages | Ouvrent ces listes, ou les ramènent au premier plan ([Listes](listes.md#listes)). |
| Affichage | Ouvrir l'onglet Grille horaire | Ouvre le calendrier ([Calendrier](grille.md#calendrier)). |
| Affichage | Ouvrir l'onglet Simulation | Ouvre la simulation ([Simulation](grille.md#simulation)). |
| Affichage | Pré-écoute… | Ouvre la fenêtre de pré-écoute ([Pré-écoute](sonores.md#pré-écoute)). |
| Diffusion | Démarrer, Arrêter, Redémarrer la diffusion | Pilotent la diffusion ([Piloter la diffusion](antenne.md#piloter-la-diffusion)). |
| Diffusion | Interrompre le sonore, la séquence, l'événement | Passent au suivant ([Interrompre l'antenne](antenne.md#interrompre-lantenne)). |
| Maintenance | Indexation rapide, Audit complet | Vérifient les sonores ([Indexation depuis l'interface](sonores.md#indexation-depuis-linterface)). |
| Maintenance | Maintenance de la base de données… | Après confirmation, sauvegarde, vérifie et optimise la base, dans une fenêtre de terminal, qui reste ouverte à la fin : la fermer une fois le compte rendu lu. La question donne le répertoire où la sauvegarde sera enregistrée, et « Choisir l'emplacement… » en propose un autre ; Entrée ou Échap l'annulent. Inactive pendant une indexation. Voir le [guide d'administration](../administration/commandes.md#maintenance-de-la-base--machin-maintenance-db). |
| Maintenance | Moniteur de la sortie… | À venir ([#85](https://github.com/dascritch/machincast/issues/85)). |
| Aide | Documentation | Ouvre ce guide dans le navigateur web. |
| Aide | Signaler un problème… | Ouvre les tickets de MachinCast dans le navigateur web. |
| Aide | Version | Donne la version de MachinCast, et la date de sa dernière modification. |

## Rafraîchir les onglets

Chaque onglet lit la base quand il s'ouvre ; ce qu'un autre poste, l'indexation ou la diffusion changent ensuite n'apparaît pas tout seul. **Affichage → Rafraîchir les onglets**, ou <kbd>F5</kbd>, relit tout d'un coup :

- l'onglet ouvert : une liste, les incidents, le calendrier ou la recherche ;
- l'airplay de l'accueil ;
- toutes les fiches ouvertes. Une fiche modifiée demande d'abord quoi faire de ses modifications : **Enregistrer** les écrit puis relit la fiche, **Abandonner** les perd et relit la fiche, **Annuler** la laisse telle quelle.
- La fiche d'un élément effacé depuis un autre poste se ferme, sans question.

La barre d'état le confirme, « Onglets rafraîchis. », et nomme les fiches laissées telles quelles ou fermées.

## Rechercher

**Affichage → Rechercher…**, ou <kbd>Ctrl</kbd>+<kbd>F</kbd>, ouvre l'onglet **Recherche**, ou y revient, le curseur dans le champ.

![La recherche de « café » : un résultat par sonore dont l'artiste ou le titre contient le texte tapé](../captures/recherche.png)

Dès 2 caractères, sans tenir compte des majuscules ni des accents, le texte tapé est cherché dans le nom interne et le nom public des **événements**, des **séquences** et des **banques**, et dans l'artiste et le titre des **sonores**. La table suit la frappe : jusqu'à 500 résultats, avec leur type, nom interne, nom public et statut (l'état d'un sonore), dans l'ordre événements, séquences, banques, puis sonores. Un double-clic ou <kbd>Entrée</kbd> sur une ligne ouvre sa fiche. Le compte dit combien il y a de résultats, ou « 500 premiers résultats sur … » quand il y en a davantage : préciser alors le texte.

## Préférences

**Fichier → Préférences…** ouvre la fenêtre des préférences.

![Les préférences, page « Interface » : les crossfades par défaut et les réglages de l'accueil](../captures/preferences.png)

Page **Interface** :

| Réglage | Rôle |
| --- | --- |
| Granularité | `Au dixième de seconde` (par défaut) ou `À la seconde` : le pas des crossfades dans les fiches. |
| Durée maximale | Le crossfade le plus long que proposent les fiches, 5 secondes par défaut. |
| Début par défaut, fin par défaut | Le crossfade d'un sonore qui n'en a pas, et que sa banque ne règle pas ([Enchaînements](antenne.md#enchaînements)). |
| Afficher le voyant de saturation de l'accueil | Cochée par défaut ; décochée, le voyant « Saturation » disparaît du [VU-mètre](#vu-mètre-de-lantenne). |
| Proposer au lancement ce qui manque pour démarrer | Cochée par défaut : la fenêtre [Pour bien démarrer](#pour-bien-démarrer). |
| Icône de l'application | L'icône des fenêtres de MachinCast, de son raccourci dans le menu des applications et sur le bureau, et de la barre des tâches. **Choisir une image…** en prend une autre, SVG, PNG ou JPEG, de préférence carrée, le logo de la radio par exemple ; **Icône de MachinCast** revient à celle d'origine. Une image illisible n'est pas prise : `Image illisible : …`. La nouvelle icône vaut dès **OK**. |

Page **Audio** :

| Réglage | Rôle |
| --- | --- |
| Antenne | Le périphérique de la diffusion. Tant qu'il n'est pas choisi, la barre d'état affiche `Périphérique de l'antenne à renseigner`, et la diffusion refuse de démarrer. Le nouveau périphérique vaut au prochain démarrage de la diffusion. |
| Pré-écoute | Le périphérique de la [pré-écoute](sonores.md#pré-écoute), le casque de la régie par exemple. L'antenne et la pré-écoute n'utilisent jamais le même : celui de l'une est grisé dans l'autre. |
| Seuil de blanc | De -100 à -0,1 dB, -40 dB par défaut : le niveau sous lequel le début et la fin d'un sonore sont un blanc ([Blancs au début et à la fin](antenne.md#blancs-au-début-et-à-la-fin)). |

**OK** les enregistre ; la barre d'état le dit. **Annuler** ne change rien.

## Textes saisis

Les noms, l'artiste, le titre et les métadonnées sont nettoyés à l'enregistrement, pour ne pas gêner la page publique, les flux et les afficheurs : les tabulations, retours à la ligne et espaces spéciales deviennent une espace simple, les espaces en trop disparaissent, et les caractères invisibles sont retirés. Les accents, les écritures non latines et les emoji restent tels quels. Les chemins de fichiers et les adresses de streams sont gardés tels quels.
