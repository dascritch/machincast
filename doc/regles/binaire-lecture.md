# Règles — Binaire lecture

À lire avant de toucher à `Machin_lecture`. Comportement complet : [spec.md § 4](../spec.md#4-règles-dordonnancement) et [§ 5](../spec.md#5-binaire-lecture).

## Rôle

Lire les événements et les jouer, rien d'autre. Le binaire tourne comme service systemd.

## Règles à ne jamais enfreindre

- Le binaire lecture ne fait que lire les fichiers sonores ([#96](https://github.com/dascritch/machincast/issues/96)) : ses sorties et sa socket d'état passent par `verifier_ecriture`, les fichiers de la simulation ont toujours l'extension `.csv`, `.pls` ou `.html`, et un sonore expiré ou introuvable ne change que la base. Voir [developpement.md](developpement.md#fichiers-sonores).
- Le début d'un événement coupe **net** le sonore en cours.
- Une banque jouée fait jouer **un seul** sonore.
- Le mode aléatoire est contrôlé : pas de répétition dans une banque avant d'avoir joué tous ses sonores. Le cycle est propre à chaque banque.
- Une banque marquée « ne pas répéter » ne passe jamais deux fois de suite, même d'un événement à l'autre : l'élément est sauté, et l'événement se termine s'il ne reste rien d'autre de jouable ([#63](https://github.com/dascritch/machincast/issues/63)).
- Seuls les sonores jouables sont candidats : à l'état `actif`, dans leur période de diffusion, sous leur maximum de lectures.
- Artiste et titre sont masqués selon la priorité Événement > Séquence > Banque > Sonore > configuration ; masqués, ils laissent la place au premier nom public renseigné, Événement > Séquence > Banque (`sorties.premier_nom_public`), sinon au texte public. Les sorties privées affichent tout, les sorties publiques appliquent le masquage.
- Jamais de diffusion sur un périphérique implicite : sans `audio.peripherique`, `Machin_lecture` refuse de diffuser (code 2), sauf sur la sortie `factice` ([#116](https://github.com/dascritch/machincast/issues/116)).
- Jamais de silence non signalé : si rien n'est jouable, émettre un silence et lever une alerte dans le log.

## Grille et événement actif

- `machincast.lecture.grille.evenement_actif(evenements, instant, terminees)` donne l'occurrence active ; c'est une fonction pure, testée avec une `HorlogeFixe` ([#12](https://github.com/dascritch/machincast/issues/12)). La grille se lit en base par `lire_grille`, avec le rôle de la lecture, sessions sautées comprises (`Evenement.sautees`, [#273](https://github.com/dascritch/machincast/issues/273)) : une session sautée est écartée par chaque fonction de la grille qui produit des occurrences (`occurrence`, `_occurrences`, `prochain_changement`) ; seules `sessions` et `prevoir`, pour le calendrier, la donnent encore.
- Le poste travaille en heure locale, celle de Paris (revue de [PR #82](https://github.com/dascritch/machincast/pull/82)) : pas de fuseau à manier. La grille convertit chaque heure en heure murale du poste (`heure_murale`) et calcule la récurrence sur ces heures murales. Les tests règlent le processus sur l'heure de Paris (`TZ`), quel que soit le poste qui les lance.
- Une occurrence terminée plus tôt (liste épuisée d'un événement sans fin) est repérée par sa clé `Occurrence.cle`, l'identifiant de l'événement et le début de l'occurrence.

## Choix d'un sonore dans une banque

- `machincast.lecture.banques.choisir_sonore(connexion, banque, instant, hasard)` ([#13](https://github.com/dascritch/machincast/issues/13)) : aucun état en mémoire, tout se déduit de l'airplay. Chaque passage doit donc noter dans `airplay.banque_id` la banque qui l'a fourni, et rien d'autre : un sonore placé directement dans un événement n'a pas de banque.
- Le tirage passe par le `Hasard` reçu, créé par `machincast.hasard.creer_hasard` : jamais d'`import random` hors de `machincast.hasard`.
- Les règles de jouabilité (§ 4.5) sont dans `banques.jouable` ; le maximum de lectures se compte sur tout l'airplay.

## Déroulé et transitions

- `machincast.lecture.deroule.Ordonnanceur.decider(instant, en_cours)` ([#14](https://github.com/dascritch/machincast/issues/14)) dit à la sortie audio de continuer, couper net, jouer un sonore ou se taire. Il ne garde en mémoire que les occurrences terminées plus tôt et l'état de silence : la position dans chaque liste se lit dans l'airplay.
- Chaque passage doit donc noter dans l'airplay son événement (`evenement_id`) et son élément (`element_id`), en plus de sa banque.
- Séquences ([#99](https://github.com/dascritch/machincast/issues/99)) : `deroule.prochain` joue un élément séquence par `dans_la_sequence`, depuis son premier élément jouable ; chaque passage note `airplay.sequence_id` et `sequence_element_id` (`Choix.ligne`). À chaque décision, `Ordonnanceur._suite` continue d'abord la séquence du dernier passage de tout l'historique, même son événement fini (au nom de cet événement), sauf si un événement a commencé depuis ce passage ou pendant la suspension d'un stream. Une séquence ne contient jamais une autre séquence. Ses lignes se lisent par `machincast.lecture.sequences`.
- Banque « ne pas répéter » ([#63](https://github.com/dascritch/machincast/issues/63)) : à chaque décision, l'ordonnanceur lit le dernier passage de tout l'historique (`Historique.dernier_passage`) ; si sa banque est marquée (`banques.a_ne_pas_repeter`), `prochain` saute les éléments qui la rappellent. Chaque élément sauté est noté une seule fois par passage (`élément sauté`, info), même si la décision est reprise ; une émission ou un spécial terminé à cause du saut donne l'alerte `événement terminé plus tôt`, pas un événement terminé pour une autre raison. `deroule.appels_ignores` donne à l'interface les lignes d'une liste qui seront toujours sautées.
- Une seule alerte `silence` par silence, pas une par seconde.
- Interruption manuelle ([#104](https://github.com/dascritch/machincast/issues/104)) : les seules entrées de l'interface vers `Machin_lecture` sont la demande d'interruption et la demande de relire la grille ([#273](https://github.com/dascritch/machincast/issues/273), `Diffusion.relire_la_grille`), sur la socket d'état (`etat.lire_demande`, `SocketEtat.demandes`) ; aucune autre commande n'y passe sans ticket. `Diffusion.interrompre` éteint le sonore avec les crossfades par défaut de la configuration (`_eteindre`, `fondu` et `montee`) ; l'ordonnanceur garde en mémoire la séquence abandonnée (`sequence_abandonnee`) et les occurrences terminées (`terminees`, `rendre_au_fil_musical`), que `anticiper` et `prevision` restaurent.
- Playlist immédiate ([#228](https://github.com/dascritch/machincast/issues/228)) : les sonores à venir (`Diffusion.a_venir`, des `Prevu`) se prévoient dans `Ordonnanceur.prevision`, avec un `HistoriquePrevu` qui compte les passages prévus comme joués et n'écrit rien. Un sonore à venir se décide toujours dans `prevision` : hors d'elle, la décision consignerait et changerait l'état de l'ordonnanceur. Le hasard n'y est pas restauré : les tirages sont engagés, et un sonore prévu ne se retire jamais au hasard tant que rien d'imprévu n'arrive. Un nouvel état de l'ordonnanceur qui doit suivre les sonores prévus se copie dans `Prevu` et s'applique dans `Ordonnanceur.engager`. Les scénarios la font tourner sur `MoteurSimule`, qui suit l'horloge du binaire.

## Moteur audio

- `machincast.lecture.moteur.MoteurAudio` ([#15](https://github.com/dascritch/machincast/issues/15)) : une voie (pipeline `playbin`) par sonore, sur l'élément de la sortie configurée (`machincast.audio.creer_sortie`). Le volume suit une enveloppe posée d'avance (GstController) d'après la durée en base. Le sonore suivant démarre à `enchainement(duree, crossfade_fin, crossfade_debut_suivant)`, avec la montée `fondu_d_entree(…)` ; sans superposition (l'un des deux crossfades à 0), la voie sortante perd son fondu (`supprimer_fondu_de_sortie`) et joue jusqu'au bout.
- Le moteur ne décide de rien : l'ordonnanceur lui dit quoi jouer et quand couper.
- `machincast.lecture.fichiers.verifier_avant_lecture` avant chaque fichier : écart consigné, fichier introuvable non joué.
- Analyse au dernier moment ([#181](https://github.com/dascritch/machincast/issues/181)) : `Diffusion._analyser`, à chaque réservation, lance l'audit complet du prochain sonore par `machincast.lecture.analyse.Analyseur`, si `a_analyser` le demande (jamais vérifié en entier, ou fichier changé, `machincast.empreinte.modifie`, partagé avec l'indexeur). Jamais d'attente : `subprocess.Popen` dans sa propre session, relevé plus tard pour ne pas laisser de zombie. Le binaire lecture n'écrit rien de la vérification : c'est l'indexeur, avec son rôle, qui met la base à jour. Sans `Analyseur` (simulation, scénarios par défaut), rien n'est lancé ; les scénarios imitent Machin indexation par un script.
- Les tests utilisent la sortie factice : en temps réel (`sync`) quand le temps compte, au plus vite sinon.

## Boucle de diffusion

- `machincast.lecture.diffusion.Diffusion` ([#88](https://github.com/dascritch/machincast/issues/88)) assemble l'ordonnanceur, le moteur, la vérification des fichiers et l'enregistrement. Elle avance par `pas()`, à l'heure de l'`Horloge` reçue : les tests la font tourner pas à pas avec une `HorlogeFixe`, sur la sortie factice, au plus vite ou en temps réel.
- Le moment d'enchaîner vient de la position de la voie (`duree - crossfade_fin`) ; les heures de l'airplay et du log viennent de l'horloge.
- Détection de blanc ([#146](https://github.com/dascritch/machincast/issues/146), [#234](https://github.com/dascritch/machincast/issues/234)) : `lire_parametres` décide seul de la partie jouée et de ses fondus (`machincast.lecture.fondus.placer`, avec les positions des fondus des préférences), et donne au moteur sa durée, son début dans le fichier (`Parametres.decalage`) et les volumes aux bords d'un fondu qui déborde du fichier (`volume_de_depart`, `volume_d_arrivee`) ; le reste de la diffusion ne voit que cette durée. Une voie dont la lecture ne commence pas au début du fichier, ou n'y finit pas (`decalage` non `None`), pré-lit son fichier puis le borne par une recherche, et compte sa position, son enveloppe et ses fondus depuis le début de sa lecture ; une voie sans décalage joue le fichier en entier, sans recherche. Les règles du placement ne s'écrivent qu'une fois, dans `fondus` : l'interface s'en sert aussi. Le fichier n'est jamais modifié.
- Un fichier introuvable est écarté par `Ordonnanceur.exclure` pendant `REESSAI_FICHIER_INTROUVABLE` ; `prochain` et `choisir_sonore` reçoivent ces sonores écartés et les traitent comme non jouables.
- Les signaux ne font que lever un `threading.Event` (`installer_arret`) : l'arrêt se fait entre deux pas, jamais au milieu d'une écriture.

## Streams

- Spec [§ 4.7](../spec.md#47-streams), [#16](https://github.com/dascritch/machincast/issues/16). Un stream n'a pas de fin : une voie de stream finie ou en erreur avant son extinction (`Lecture.eteinte`) est un flux tombé, jamais une fin normale.
- `Ordonnanceur.suspendre` remplace l'occurrence du stream tombé par son événement de secours, ou par l'événement inférieur ; toute autre occurrence active lève la suspension. `Decision.eteindre` demande d'éteindre un stream à la fin de son événement.
- La reconnexion passe par une voie muette (`MoteurAudio.jouer(..., muette=True)`), retentée tous les `Diffusion.delai_reconnexion` ; la source HTTP ne retente rien d'elle-même (`retries` à 0). Le flux est revenu dès que la position de la voie avance.
- Les événements de secours ne sont jamais dans la grille : `lire_grille` les écarte, `lire_evenement` les lit.
- Les scénarios des streams utilisent un serveur HTTP local ([`tests/flux.py`](../../tests/flux.py)), qui envoie le flux au rythme du temps réel ; aucun accès au réseau.

## Expiration

- `machincast.lecture.expiration.expirer(connexion, instant, sonore=None)` ([#18](https://github.com/dascritch/machincast/issues/18)) : une seule requête `UPDATE … RETURNING` passe à `expire` les sonores `actif` arrivés au bout, puis consigne chacun. Le `RETURNING` est permis sur `sonores`, que la lecture peut lire, jamais sur `log`.
- La diffusion vérifie le sonore de chaque passage qui commence, et tous les sonores au démarrage puis toutes les `VERIFICATION_DES_EXPIRATIONS`.

## Sorties

- `machincast.lecture.sorties.Sorties` ([#19](https://github.com/dascritch/machincast/issues/19)) : la diffusion l'appelle à chaque passage qui commence (`passage_commence`) et qui finit (`passage_termine`). La page HTML et la playlist se recalculent depuis l'airplay, et survivent donc à un redémarrage ; le CSV du jour reçoit une ligne par passage terminé.
- Le masquage ne s'applique qu'à la sortie publique : `masque(masquages, defaut)` prend le premier niveau renseigné, événement, séquence, banque, sonore, sinon la configuration.
- Une sortie ne doit jamais arrêter la diffusion : toute `OSError` à l'écriture devient une alerte `sortie inaccessible`, une fois par chemin.
- Les tests écrivent leurs sorties dans leur répertoire temporaire, jamais aux chemins de la configuration de test.
- `consigner` recopie les alertes et incidents dans le journal du binaire (sortie d'erreur).

## Écritures autorisées

Connexion par `machincast.base.connecter(…, Role.LECTURE)`. Ces écritures sont garanties par les droits PostgreSQL ([spec.md § 3.2](../spec.md#32-rôles-et-droits)). L'airplay et le log ne s'écrivent que par `machincast.lecture.enregistrement` (`commencer_passage`, `terminer_passage`, `consigner`) : un scénario d'`enregistrement.feature` refuse tout autre `INSERT INTO log` dans le binaire lecture ([#17](https://github.com/dascritch/machincast/issues/17)).

- `airplay` : une ligne de début et une ligne de fin par passage.
- `log` : toutes les opérations, normales et incidents. Le rôle ne peut pas lire cette table : pas de `RETURNING` sur une insertion dans `log`.
- `sonores.etat` : passage à `expire` au maximum de lectures ou à la fin de la période de diffusion, toujours consigné dans le log ; jamais un autre état ([#66](https://github.com/dascritch/machincast/issues/66)).

## Mode simulation

Aucune écriture en base, aucune sortie sonore, état tenu en mémoire, graine reproductible, sorties .csv, .pls et .html nommées à part ([#21](https://github.com/dascritch/machincast/issues/21), [spec.md § 5.5](../spec.md#55-mode-simulation)).

- La simulation rejoue la vraie `Diffusion` : toute règle de lecture vaut donc pour les deux. Un nouvel accès à l'airplay ou au log passe par l'`Historique` (`machincast.lecture.historique`), jamais par une requête directe dans un autre module : sinon la simulation ne verrait pas ses propres passages.
- Toute la simulation tient dans `lecture_seule` : une transaction `READ ONLY` que PostgreSQL protège lui-même. Un scénario vérifie qu'une écriture y est refusée.
- `Diffusion` attend un `Moteur` et des `VoieLecture` (`machincast.lecture.moteur`) : `MoteurAudio` à l'antenne, `MoteurSimule` en simulation.

## Interfaces exposées

- Socket Unix d'état pour l'interface graphique ([#20](https://github.com/dascritch/machincast/issues/20), `machincast.lecture.etat.SocketEtat`) : format décrit dans [spec.md § 5.4](../spec.md#54-socket-détat). Tout champ ajouté au message s'y ajoute : un scénario d'`etat.feature` vérifie que chaque champ y figure. Changer le sens d'un champ ou en retirer un augmente `VERSION`.
- La socket ne doit jamais bloquer la diffusion : un fil par client, et `publier` ne fait que déposer le dernier message.
- Le prochain sonore est réservé au début de chaque passage (`Ordonnanceur.reserver`, sans alerte de silence), et revalidé avant d'être joué (`Ordonnanceur.valider`).
- Sortie audio GStreamer choisie dans la configuration (ALSA, PulseAudio, PipeWire).
