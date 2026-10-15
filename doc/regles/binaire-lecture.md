# Règles — Binaire lecture

À lire avant de toucher à `Machin_lecture`. Comportement complet : [spec.md § 4](../spec.md#4-règles-dordonnancement) et [§ 5](../spec.md#5-binaire-lecture).

## Rôle

Lire les événements et les jouer, rien d'autre. Le binaire tourne comme service systemd.

## Règles à ne jamais enfreindre

- Le début d'un événement coupe **net** le sonore en cours.
- Une banque jouée fait jouer **un seul** sonore.
- Le mode aléatoire est contrôlé : pas de répétition dans une banque avant d'avoir joué tous ses sonores. Le cycle est propre à chaque banque.
- Une banque marquée « ne pas répéter » ne passe jamais deux fois de suite, même d'un événement à l'autre : l'élément est sauté, et l'événement se termine s'il ne reste rien d'autre de jouable ([#63](https://github.com/dascritch/machincast/issues/63)).
- Seuls les sonores jouables sont candidats : à l'état `actif`, dans leur période de diffusion, sous leur maximum de lectures.
- Artiste et titre sont masqués selon la priorité Événement > Banque > Sonore > configuration. Les sorties privées affichent tout, les sorties publiques appliquent le masquage.
- Jamais de silence non signalé : si rien n'est jouable, émettre un silence et lever une alerte dans le log.

## Grille et événement actif

- `machincast.lecture.grille.evenement_actif(evenements, instant, terminees)` donne l'occurrence active ; c'est une fonction pure, testée avec une `HorlogeFixe` ([#12](https://github.com/dascritch/machincast/issues/12)). La grille se lit en base par `lire_grille`, avec le rôle de la lecture.
- Le poste travaille en heure locale, celle de Paris (revue de [PR #82](https://github.com/dascritch/machincast/pull/82)) : pas de fuseau à manier. La grille convertit chaque heure en heure murale du poste (`heure_murale`) et calcule la récurrence sur ces heures murales. Les tests règlent le processus sur l'heure de Paris (`TZ`), quel que soit le poste qui les lance.
- Une occurrence terminée plus tôt (liste épuisée d'un événement sans fin) est repérée par sa clé `Occurrence.cle`, l'identifiant de l'événement et le début de l'occurrence.

## Choix d'un sonore dans une banque

- `machincast.lecture.banques.choisir_sonore(connexion, banque, instant, hasard)` ([#13](https://github.com/dascritch/machincast/issues/13)) : aucun état en mémoire, tout se déduit de l'airplay. Chaque passage doit donc noter dans `airplay.banque_id` la banque qui l'a fourni, et rien d'autre : un sonore placé directement dans un événement n'a pas de banque.
- Le tirage passe par le `Hasard` reçu, créé par `machincast.hasard.creer_hasard` : jamais d'`import random` hors de `machincast.hasard`.
- Les règles de jouabilité (§ 4.5) sont dans `banques.jouable` ; le maximum de lectures se compte sur tout l'airplay.

## Déroulé et transitions

- `machincast.lecture.deroule.Ordonnanceur.decider(instant, en_cours)` ([#14](https://github.com/dascritch/machincast/issues/14)) dit à la sortie audio de continuer, couper net, jouer un sonore ou se taire. Il ne garde en mémoire que les occurrences terminées plus tôt et l'état de silence : la position dans chaque liste se lit dans l'airplay.
- Chaque passage doit donc noter dans l'airplay son événement (`evenement_id`) et son élément (`element_id`), en plus de sa banque.
- Une seule alerte `silence` par silence, pas une par seconde.

## Moteur audio

- `machincast.lecture.moteur.MoteurAudio` ([#15](https://github.com/dascritch/machincast/issues/15)) : une voie (pipeline `playbin`) par sonore, sur l'élément de la sortie configurée (`machincast.audio.creer_sortie`). Le volume suit une enveloppe posée d'avance (GstController) d'après la durée en base. Le sonore suivant démarre à `enchainement(duree, crossfade_fin, crossfade_debut_suivant)`, avec la montée `fondu_d_entree(…)` ; sans superposition (l'un des deux crossfades à 0), la voie sortante perd son fondu (`supprimer_fondu_de_sortie`) et joue jusqu'au bout.
- Le moteur ne décide de rien : l'ordonnanceur lui dit quoi jouer et quand couper.
- `machincast.lecture.fichiers.verifier_avant_lecture` avant chaque fichier : écart consigné, fichier introuvable non joué.
- Les tests utilisent la sortie factice : en temps réel (`sync`) quand le temps compte, au plus vite sinon.

## Écritures autorisées

Connexion par `machincast.base.connecter(…, Role.LECTURE)`. Ces écritures sont garanties par les droits PostgreSQL ([spec.md § 3.2](../spec.md#32-rôles-et-droits)). L'airplay et le log ne s'écrivent que par `machincast.lecture.enregistrement` (`commencer_passage`, `terminer_passage`, `consigner`) : un scénario d'`enregistrement.feature` refuse tout autre `INSERT INTO log` dans le binaire lecture ([#17](https://github.com/dascritch/machincast/issues/17)).

- `airplay` : une ligne de début et une ligne de fin par passage.
- `log` : toutes les opérations, normales et incidents. Le rôle ne peut pas lire cette table : pas de `RETURNING` sur une insertion dans `log`.
- `sonores.etat` : passage à `expire` au maximum de lectures ou à la fin de la période de diffusion, toujours consigné dans le log ; jamais un autre état ([#66](https://github.com/dascritch/machincast/issues/66)).

## Mode simulation

Aucune écriture en base, aucune sortie sonore, état tenu en mémoire, graine reproductible, sorties .csv, .pls et .html nommées à part.

## Interfaces exposées

- Socket Unix d'état pour l'interface graphique.
- Sortie audio GStreamer choisie dans la configuration (ALSA, PulseAudio, PipeWire).
