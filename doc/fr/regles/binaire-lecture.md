# Règles — Binaire lecture

À lire avant de toucher à `Machin_player`. Comportement complet : [spec.md § 4](../spec.md#4-règles-dordonnancement) et [§ 5](../spec.md#5-binaire-lecture).

## Rôle

Lire les événements et les jouer, rien d'autre. Le binaire tourne comme service systemd.

## Règles à ne jamais enfreindre

- Le binaire lecture ne fait que lire les fichiers sonores ([#96](https://github.com/dascritch/machincast/issues/96)) : ses sorties et sa socket d'état passent par `check_writing`, les fichiers de la simulation ont toujours l'extension `.csv`, `.pls` ou `.html`, et un sonore expiré ou introuvable ne change que la base. Voir [developpement.md](developpement.md#fichiers-sonores).
- Le début d'un événement coupe **net** le sonore en cours.
- Une banque jouée fait jouer **un seul** sonore.
- Le mode aléatoire est contrôlé : pas de répétition dans une banque avant d'avoir joué tous ses sonores. Le cycle est propre à chaque banque.
- Une banque marquée « ne pas répéter » ne passe jamais deux fois de suite, même d'un événement à l'autre : l'élément est sauté, et l'événement se termine s'il ne reste rien d'autre de jouable ([#63](https://github.com/dascritch/machincast/issues/63)).
- Seuls les sonores jouables sont candidats : à l'état `active`, dans leur période de diffusion, sous leur maximum de lectures.
- Artiste et titre sont masqués selon la priorité Événement > Séquence > Banque > Sonore > configuration ; masqués, ils laissent la place au premier nom public renseigné, Événement > Séquence > Banque (`outputs.first_public_name`), sinon au texte public. Les sorties privées affichent tout, les sorties publiques appliquent le masquage.
- Jamais de diffusion sur un périphérique implicite : sans `audio.device`, `Machin_player` refuse de diffuser (code 2), sauf sur la sortie `factice` ([#116](https://github.com/dascritch/machincast/issues/116)).
- Jamais de blanc non signalé : si rien n'est jouable, laisser un blanc et lever une alerte dans le log.

## Grille et événement actif

- `machincast.player.grid.active_event(evenements, instant, terminees)` donne l'occurrence active ; c'est une fonction pure, testée avec une `FixedClock` ([#12](https://github.com/dascritch/machincast/issues/12)). La grille se lit en base par `read_grid`, avec le rôle de la lecture, sessions sautées comprises (`Event.skipped_list`, [#273](https://github.com/dascritch/machincast/issues/273)) : une session sautée est écartée par chaque fonction de la grille qui produit des occurrences (`occurrence`, `_occurrences`, `next_change`) ; seules `sessions` et `prevoir`, pour le calendrier, la donnent encore.
- Le poste travaille en heure locale, celle de Paris (revue de [PR #82](https://github.com/dascritch/machincast/pull/82)) : pas de fuseau à manier. La grille convertit chaque heure en heure murale du poste (`wall_hour`) et calcule la récurrence sur ces heures murales. Les tests règlent le processus sur l'heure de Paris (`TZ`), quel que soit le poste qui les lance.
- Une occurrence terminée plus tôt (liste épuisée d'un événement sans fin) est repérée par sa clé `Occurrence.key`, l'identifiant de l'événement et le début de l'occurrence.

## Choix d'un sonore dans une banque

- `machincast.player.banks.choose_sound(connexion, banque, instant, hasard)` ([#13](https://github.com/dascritch/machincast/issues/13)) : aucun état en mémoire, tout se déduit de l'airplay. Chaque passage doit donc noter dans `airplay.bank_id` la banque qui l'a fourni, et rien d'autre : un sonore placé directement dans un événement n'a pas de banque.
- Le tirage passe par le `Hasard` reçu, créé par `machincast.randomness.create_randomness` : jamais d'`import random` hors de `machincast.randomness`.
- Les règles de jouabilité (§ 4.5) sont dans `banks.playable` ; le maximum de lectures se compte sur tout l'airplay.

## Déroulé et transitions

- `machincast.player.rundown.Scheduler.decide(instant, ongoing)` ([#14](https://github.com/dascritch/machincast/issues/14)) dit à la sortie audio de continuer, couper net, jouer un sonore ou se taire. Il ne garde en mémoire que les occurrences terminées plus tôt, l'occurrence avancée (`Scheduler.advanced`, [#257](https://github.com/dascritch/machincast/issues/257)) et l'état de blanc : la position dans chaque liste se lit dans l'airplay. L'occurrence active se demande toujours à `Scheduler._active`, jamais à `grid.active_event` directement : il y ajoute l'occurrence avancée, avec l'heure où elle a commencé (`Occurrence.started`), d'où se compte sa liste.
- Chaque passage doit donc noter dans l'airplay son événement (`event_id`) et son élément (`event_item_id`), en plus de sa banque.
- Séquences ([#99](https://github.com/dascritch/machincast/issues/99)) : `rundown.next_` joue un élément séquence par `in_sequence`, depuis son premier élément jouable ; chaque passage note `airplay.sequence_id` et `sequence_item_id` (`Choice.line`). À chaque décision, `Scheduler._remainder` continue d'abord la séquence du dernier passage de tout l'historique, même son événement fini (au nom de cet événement), sauf si un événement a commencé depuis ce passage ou pendant la suspension d'un stream. Une séquence ne contient jamais une autre séquence. Ses lignes se lisent par `machincast.player.sequences`.
- Banque « ne pas répéter » ([#63](https://github.com/dascritch/machincast/issues/63)) : à chaque décision, l'ordonnanceur lit le dernier passage de tout l'historique (`History.last_play`) ; si sa banque est marquée (`banks.has_no_repeat`), `prochain` saute les éléments qui la rappellent. Chaque élément sauté est noté une seule fois par passage (`élément sauté`, info), même si la décision est reprise ; une émission ou un spécial terminé à cause du saut donne l'alerte `événement terminé plus tôt`, pas un événement terminé pour une autre raison. `rundown.ignored_calls` donne à l'interface les lignes d'une liste qui seront toujours sautées.
- Une seule alerte `blanc` par blanc, pas une par seconde.
- Interruption manuelle ([#104](https://github.com/dascritch/machincast/issues/104)) : les seules entrées de l'interface vers `Machin_player` sont la demande d'interruption et la demande de relire la grille ([#273](https://github.com/dascritch/machincast/issues/273), `Broadcast.reread_grid`), sur la socket d'état (`state.read_request`, `StateSocket.requests`) ; aucune autre commande n'y passe sans ticket. `Broadcast.interrupt` éteint le sonore avec les crossfades par défaut de la configuration (`_switch_off`, `fondu` et `montee`) ; l'ordonnanceur garde en mémoire la séquence abandonnée (`abandoned_sequence`) et les occurrences terminées (`terminees`, `return_to_background_programming`), que `anticiper` et `prevision` restaurent.
- Playlist immédiate ([#228](https://github.com/dascritch/machincast/issues/228)) : les sonores à venir (`Broadcast.upcoming`, des `Prevu`) se prévoient dans `Scheduler.forecast`, avec un `PlannedHistory` qui compte les passages prévus comme joués et n'écrit rien. Un sonore à venir se décide toujours dans `prevision` : hors d'elle, la décision consignerait et changerait l'état de l'ordonnanceur. Le hasard n'y est pas restauré : les tirages sont engagés, et un sonore prévu ne se retire jamais au hasard tant que rien d'imprévu n'arrive. Un nouvel état de l'ordonnanceur qui doit suivre les sonores prévus se copie dans `Prevu` et s'applique dans `Scheduler.engage`. Les scénarios la font tourner sur `SimulatedEngine`, qui suit l'horloge du binaire. `GRID_FINGERPRINT` ne prend que ce qui règle l'antenne ([#266](https://github.com/dascritch/machincast/issues/266)) : une colonne qui ne change ni les occurrences, ni les listes, n'y entre pas, sinon chaque enregistrement d'une fiche retirerait les sonores déjà tirés ; `Broadcast.reread_grid` ne recalcule que si elle a changé.

## Moteur audio

- `machincast.player.engine.AudioEngine` ([#15](https://github.com/dascritch/machincast/issues/15)) : une voie (pipeline `playbin3`, `machincast.audio.PLAYER`, [#284](https://github.com/dascritch/machincast/issues/284)) par sonore, sur l'élément de la sortie configurée (`machincast.audio.create_output`). Le volume suit une enveloppe posée d'avance (GstController) d'après la durée en base. Le sonore suivant démarre à `enchainement(duree, crossfade_end, following_start_crossfade)`, avec la montée `entry_fade(…)` ; sans superposition (l'un des deux crossfades à 0), la voie sortante perd son fondu (`delete_output_fade`) et joue jusqu'au bout.
- Le moteur ne décide de rien : l'ordonnanceur lui dit quoi jouer et quand couper.
- `machincast.player.files.check_before_playback` avant chaque fichier : écart consigné, fichier introuvable non joué.
- Une voie qui n'atteint pas l'état PLAYING dans `GUARD_DELAY` est bloquée (`Track.blocked`, [#281](https://github.com/dascritch/machincast/issues/281)) : la diffusion la coupe, termine son passage en incident `lecture bloquée` et joue le suivant. L'horloge des voies est `time.monotonic`, injectée (`AudioEngine(horloge=…)`) : les scénarios la remplacent ; toute voie (`PlaybackTrack`) répond à `bloquee`, la voie simulée jamais.
- Un seul délai de garde, `GUARD_DELAY` (10 s, celui de la connexion d'un flux HTTP/1.1, `CONNECTION_DELAY_SECONDS`), dans tous les cas ([#278](https://github.com/dascritch/machincast/issues/278)) : lecture bloquée au démarrage, stream gelé (`Track.frozen`, position qui n'avance plus, demandée à chaque pas), sonde sans son. Un stream gelé est un flux tombé (`Broadcast._discard_frozen_stream`), même sans erreur de GStreamer. Les flux se lisent en HTTP/1.1 (`SOUP_FORCE_HTTP1`, `machincast/__init__.py`) ; un nouveau programme qui lit des flux importe le paquet `machincast` avant GStreamer, ce que fait tout module du projet.
- Blanc dans un sonore ([#122](https://github.com/dascritch/machincast/issues/122)) : le niveau se mesure dans la voie, par un élément `level` avant `volume` (`Track.dead_air`, `Track.heard`, lus à `traiter`) ; toute voie (`PlaybackTrack`) y répond, la voie simulée jamais en blanc. La diffusion ne regarde que le sonore en cours (`Broadcast._handle_dead_air`). Avec `DeadAirSettings.fallback`, un stream en blanc garde sa voie comme sonde (`Probe.dead_air`), qui ne reprend qu'avec du son. Le moteur reçoit la durée et le seuil (`AudioEngine(blanc=…)`), la diffusion le passage au secours (`Diffusion(dead_air=…)`), tous deux de `configuration.dead_air`. Un blanc n'est ni un silence ([#291](https://github.com/dascritch/machincast/issues/291)) ni l'alerte `blanc`.
- Analyse au dernier moment ([#181](https://github.com/dascritch/machincast/issues/181)) : `Broadcast._analyse`, à chaque réservation, lance l'audit complet du prochain sonore par `machincast.player.analysis.Analyser`, si `to_analyse` le demande : pas d'audit complet depuis la dernière modification du fichier ([#401](https://github.com/dascritch/machincast/issues/401), `machincast.fingerprint.audited_since_modification`, partagé avec l'indexeur, dont `already_audited` y ajoute le seuil de silence). Jamais d'attente : `subprocess.Popen` dans sa propre session, relevé plus tard pour ne pas laisser de zombie. Le binaire lecture n'écrit rien de la vérification : c'est l'indexeur, avec son rôle, qui met la base à jour. Sans `Analyseur` (simulation, scénarios par défaut), rien n'est lancé ; les scénarios imitent Machin indexer par un script.
- Les tests utilisent la sortie factice : en temps réel (`sync`) quand le temps compte, au plus vite sinon.

## Boucle de diffusion

- `machincast.player.broadcast.Broadcast` ([#88](https://github.com/dascritch/machincast/issues/88)) assemble l'ordonnanceur, le moteur, la vérification des fichiers et l'enregistrement. Elle avance par `pas()`, à l'heure de l'`Horloge` reçue : les tests la font tourner pas à pas avec une `FixedClock`, sur la sortie factice, au plus vite ou en temps réel.
- Le moment d'enchaîner vient de la position de la voie (`duree - crossfade_end`) ; les heures de l'airplay et du log viennent de l'horloge.
- Détection de silence ([#146](https://github.com/dascritch/machincast/issues/146), [#234](https://github.com/dascritch/machincast/issues/234)) : `read_parameters` décide seul de la partie jouée et de ses fondus (`machincast.player.fades.put`, avec les positions des fondus des préférences), et donne au moteur sa durée, son début dans le fichier (`Parameters.offset`) et les volumes aux bords d'un fondu qui déborde du fichier (`departure_volume`, `arrival_volume`) ; le reste de la diffusion ne voit que cette durée. Une voie dont la lecture ne commence pas au début du fichier, ou n'y finit pas (`decalage` non `None`), pré-lit son fichier puis le borne par une recherche, et compte sa position, son enveloppe et ses fondus depuis le début de sa lecture ; une voie sans décalage joue le fichier en entier, sans recherche. Les règles du placement ne s'écrivent qu'une fois, dans `fondus` : l'interface s'en sert aussi. Le fichier n'est jamais modifié.
- Un fichier introuvable est écarté par `Scheduler.exclude` pendant `NOT_FOUND_FILE_RETRY` ; `prochain` et `choose_sound` reçoivent ces sonores écartés et les traitent comme non jouables.
- Les signaux ne font que lever un `threading.Event` (`install_stop`) : l'arrêt se fait entre deux pas, jamais au milieu d'une écriture.

## Streams

- Spec [§ 4.7](../spec.md#47-streams), [#16](https://github.com/dascritch/machincast/issues/16). Un stream n'a pas de fin : une voie de stream finie ou en erreur avant son extinction (`Playback.off`) est un flux tombé, jamais une fin normale.
- `Scheduler.suspend` remplace l'occurrence du stream tombé par son événement de secours, ou par l'événement inférieur ; toute autre occurrence active lève la suspension. `Decision.switch_off` demande d'éteindre un stream à la fin de son événement.
- La reconnexion passe par une voie muette (`AudioEngine.play(..., muette=True)`), retentée tous les `Broadcast.reconnection_delay` ; la source HTTP ne retente rien d'elle-même (`retries` à 0). Le flux est revenu dès que la position de la voie avance.
- Les événements de secours ne sont jamais dans la grille : `read_grid` les écarte, `read_event` les lit.
- Les scénarios des streams utilisent un serveur HTTP local ([`tests/stream.py`](../../../tests/stream.py)), qui envoie le flux au rythme du temps réel ; aucun accès au réseau.

## Expiration

- `machincast.player.expiry.expire(connexion, instant, sonore=None)` ([#18](https://github.com/dascritch/machincast/issues/18)) : une seule requête `UPDATE … RETURNING` passe à `expired` les sonores `active` arrivés au bout, puis consigne chacun. Le `RETURNING` est permis sur `sounds`, que la lecture peut lire, jamais sur `log`.
- La diffusion vérifie le sonore de chaque passage qui commence, et tous les sonores au démarrage puis toutes les `EXPIRY_CHECK`.

## Sorties

- `machincast.player.outputs.Outputs` ([#19](https://github.com/dascritch/machincast/issues/19)) : la diffusion l'appelle à chaque passage qui commence (`started_play`) et qui finit (`finished_play`). La page HTML et la playlist se recalculent depuis l'airplay, et survivent donc à un redémarrage ; le CSV du jour reçoit une ligne par passage terminé.
- Le masquage ne s'applique qu'à la sortie publique : `masque(masquages, defaut)` prend le premier niveau renseigné, événement, séquence, banque, sonore, sinon la configuration.
- Une sortie ne doit jamais arrêter la diffusion : toute `OSError` à l'écriture devient une alerte `sortie inaccessible`, une fois par chemin.
- Les tests écrivent leurs sorties dans leur répertoire temporaire, jamais aux chemins de la configuration de test.
- `consigner` recopie les alertes et incidents dans le journal du binaire (sortie d'erreur).

## Écritures autorisées

Connexion par `machincast.database.open_connection(…, Role.PLAYBACK)`. Ces écritures sont garanties par les droits PostgreSQL ([spec.md § 3.2](../spec.md#32-rôles-et-droits)). L'airplay et le log ne s'écrivent que par `machincast.player.saving` (`begin_play`, `finish_play`, `consigner`) : un scénario d'`saving.feature` refuse tout autre `INSERT INTO log` dans le binaire lecture ([#17](https://github.com/dascritch/machincast/issues/17)).

- `airplay` : une ligne de début et une ligne de fin par passage.
- `log` : toutes les opérations, normales et incidents. Le rôle ne peut pas lire cette table : pas de `RETURNING` sur une insertion dans `log`.
- `sounds.state` : passage à `expired` au maximum de lectures ou à la fin de la période de diffusion, toujours consigné dans le log ; jamais un autre état ([#66](https://github.com/dascritch/machincast/issues/66)).

## Mode simulation

Aucune écriture en base, aucune sortie sonore, état tenu en mémoire, graine reproductible, sorties .csv, .pls et .html nommées à part ([#21](https://github.com/dascritch/machincast/issues/21), [spec.md § 5.5](../spec.md#55-mode-simulation)).

- La simulation rejoue la vraie `Diffusion` : toute règle de lecture vaut donc pour les deux. Un nouvel accès à l'airplay ou au log passe par l'`Historique` (`machincast.player.history`), jamais par une requête directe dans un autre module : sinon la simulation ne verrait pas ses propres passages.
- Toute la simulation tient dans `read_only` : une transaction `READ ONLY` que PostgreSQL protège lui-même. Un scénario vérifie qu'une écriture y est refusée.
- `Diffusion` attend un `Moteur` et des `PlaybackTrack` (`machincast.player.engine`) : `AudioEngine` à l'antenne, `SimulatedEngine` en simulation.

## Interfaces exposées

- Socket Unix d'état pour l'interface graphique ([#20](https://github.com/dascritch/machincast/issues/20), `machincast.player.state.StateSocket`) : format décrit dans [spec.md § 5.4](../spec.md#54-socket-détat). Tout champ ajouté au message s'y ajoute : un scénario d'`state.feature` vérifie que chaque champ y figure. Changer le sens d'un champ ou en retirer un augmente `VERSION`.
- La socket ne doit jamais bloquer la diffusion : un fil par client, et `publier` ne fait que déposer le dernier message.
- Le prochain sonore est réservé au début de chaque passage (`Scheduler.reserve`, sans alerte de blanc), et revalidé avant d'être joué (`Scheduler.validate`).
- Sortie audio GStreamer choisie dans la configuration (ALSA, PulseAudio, PipeWire).
