# Dépannage

Les pannes connues de MachinCast, leurs causes, ce qu'il faut vérifier, et les scénarios qui les surveillent. Les messages du journal se lisent par `Machin logs` (la diffusion), ou dans l'onglet **Incidents** de l'interface.

## Un stream tombe, mais l'antenne reste sur un blanc

**Symptôme** : un stream tombe, par exemple quand le réseau est coupé. L'antenne reste sur un blanc, sans repli sur l'événement de secours ni sur le fil musical, et le journal ne note aucun `flux tombé`. Quand le réseau revient, le stream ne reprend pas : il faut relancer la diffusion.

**Cause** ([#278](https://github.com/dascritch/machincast/issues/278)) : le flux est servi en **HTTP/2**, souvent derrière un serveur nginx, comme celui de France Inter. En HTTP/2, libsoup 3, la bibliothèque par laquelle GStreamer lit les streams, ne signale pas qu'une connexion ne donne plus rien ([ticket 256 de libsoup](https://gitlab.gnome.org/GNOME/libsoup/-/issues/256), [ticket 367 de libsoup](https://gitlab.gnome.org/GNOME/libsoup/-/issues/367), [ticket 296 de libsoup](https://gitlab.gnome.org/GNOME/libsoup/-/issues/296)) : le lecteur attend sans fin, sans erreur. Un flux servi en HTTP/1.1, comme un Icecast direct, n'est pas touché. Le type du flux (MP3, AAC) n'y est pour rien. Un autre lecteur bâti sur GStreamer a contourné le même défaut de la même façon ([ticket 252 de sone](https://github.com/lullabyX/sone/issues/252)).

**Ce que fait MachinCast** :

- Il lit tous ses flux en HTTP/1.1 : la variable `SOUP_FORCE_HTTP1` est posée au lancement de chacun de ses programmes. Le délai de 10 secondes de la connexion s'applique alors, et le lecteur signale le flux tombé.
- Il tient aussi pour tombé un stream dont la lecture n'avance plus pendant **10 secondes**, le même délai de garde que pour une lecture bloquée et pour la connexion d'un flux en HTTP/1.1, même si le lecteur ne signale rien. Le journal note alors `flux tombé` : « plus de son depuis 10 secondes, sans erreur du lecteur ».
- La reconnexion reprend le stream dès que du son revient.

**À vérifier** :

- La version de HTTP d'un flux : `curl -I <adresse>`. La première ligne dit `HTTP/2 200` ou `HTTP/1.1 200`.
- Le journal pendant la panne : `Machin logs`. Un `flux tombé` doit apparaître une dizaine de secondes après la coupure, un peu plus si le lecteur avait du son d'avance, puis `reprise du flux` après son retour.
- Si l'antenne reste encore sur un blanc sans `flux tombé`, ouvrir un ticket avec le journal, l'adresse du flux et la réponse de `curl -I`.

## L'interface se ferme d'un coup : pré-écoute, préférences audio, session verrouillée, écrans en veille

**Symptôme** : l'interface se ferme sans message, en ouvrant la pré-écoute, en changeant sa sortie, en ouvrant la page « Audio » des préférences, ou au retour d'une session verrouillée ou d'écrans en veille. Le terminal, s'il y en a un, montre `Fatal Python error: Aborted`, `Segmentation fault` ou `double free or corruption`, dans `gst_device_monitor_stop`, `g_slist_delete_link`, ou un fil de PipeWire (`libgstpipewire.so`, `libpipewire-module-metadata.so`) ; `coredumpctl list` en garde la trace.

**Cause** : un défaut de GStreamer 1.28.0 à 1.28.2, celui d'Ubuntu 26.04 ([#289](https://github.com/dascritch/machincast/issues/289)). La liste des périphériques audio arrêtait le moniteur de périphériques avant qu'il ait fini de démarrer. Depuis [#289](https://github.com/dascritch/machincast/issues/289), MachinCast attend ce démarrage, et la liste est aussi complète. GStreamer 1.28.3 corrige le défaut de son côté. Avec PipeWire 1.6.2, arrêter le moniteur pendant que des sorties apparaissent ou disparaissent, comme une sortie HDMI quand l'écran se met en veille, tuait aussi l'interface ([#305](https://github.com/dascritch/machincast/issues/305)) : depuis, l'interface garde un seul moniteur, ouvert jusqu'à sa fermeture.

**À vérifier** :

- La version de MachinCast : une installation d'avant [#305](https://github.com/dascritch/machincast/issues/305) se met à jour par `git pull`, puis `./install.sh`.
- Le journal de l'interface : « le moniteur de périphériques n'a pas fini de démarrer en 5 secondes » dit qu'un fournisseur de périphériques, PipeWire, PulseAudio ou ALSA, met trop longtemps à répondre. La liste peut alors être incomplète ; l'interface ne se ferme pas. Vérifier que le serveur audio tourne : `systemctl --user status pipewire`.
- `python -m tests.mesures_peripheriques --bascule`, depuis le dépôt, mesure le défaut sur le poste, pendant qu'une sortie apparaît et disparaît ([Mesurer la liste des périphériques audio](doc/developpement/poste.md#mesurer-la-liste-des-périphériques-audio)).

**Scénario qui le surveille** : « La liste des périphériques du poste, en boucle, ne fait jamais tomber son processus », dans `tests/features/peripheriques_liste.feature`, à chaque passage des tests.

## Des sons du bureau passent à l'antenne

**Symptôme** : une notification, le son d'une vidéo, d'une visioconférence ou du navigateur s'entend à l'antenne, par-dessus la diffusion.

**Cause** ([#250](https://github.com/dascritch/machincast/issues/250)) : le périphérique de l'antenne est la sortie par défaut du bureau, celle de tous les programmes qui n'en choisissent pas. MachinCast n'y est pour rien : `Machin lecture` joue sur `audio.peripherique`, quelle que soit la sortie par défaut.

**À vérifier** :

- `pactl get-default-sink` ne doit pas donner l'identifiant de `audio.peripherique`. Sinon, choisir une autre sortie par défaut, et couper les sons de notification : voir [Préparer le poste d'antenne](INSTALL.md#préparer-le-poste-dantenne).
- `wpctl status`, sous PipeWire, liste dans « Streams » les programmes qui jouent, et sur quelle sortie.

## La pré-écoute s'arrête, ou le VU-mètre se rouvre, au retour d'un écran éteint

**Symptôme** : au retour d'une session verrouillée ou d'un écran en veille, la pré-écoute s'est arrêtée (« Lecture impossible : … »), ou le VU-mètre de l'antenne dit un moment « Indisponible : le port de monitoring ne donne plus rien depuis 3 secondes. ».

**Cause** : à la mise en veille de l'écran, des sorties audio disparaissent, comme celle de l'écran HDMI, et le serveur audio du poste peut interrompre les flux en cours. La pré-écoute s'arrête alors, et le dit ([#259](https://github.com/dascritch/machincast/issues/259)) ; le VU-mètre ne garde pas ses derniers niveaux, et rouvre son port toutes les 5 secondes, jusqu'à ce que le son revienne ([#311](https://github.com/dascritch/machincast/issues/311)). La diffusion n'est pas touchée.

**À vérifier** :

- Que l'écran du poste d'antenne ne se met pas en veille : voir [Préparer le poste d'antenne](INSTALL.md#préparer-le-poste-dantenne) ([#250](https://github.com/dascritch/machincast/issues/250)).
- Relancer la pré-écoute une fois le son revenu. Si le VU-mètre reste indisponible plus de 10 secondes, vérifier que le serveur audio tourne (`systemctl --user status pipewire`), puis ouvrir un ticket avec la sortie console de `Machin interface`.

## Scénarios à lancer avant une version

Certains scénarios ne tournent ni avec `pytest`, ni avec `bin/Machin dev-test` : ils sont lents, ou ont besoin d'un serveur à part. Ils sont marqués `@release`, et se lancent avant chaque version ([#208](https://github.com/dascritch/machincast/issues/208)), et après toute mise à jour de GStreamer ou de libsoup :

```bash
.venv/bin/pytest -m release
```

Ils demandent les dépendances de test (`./install.sh --dev`, ou `pip install --editable ".[dev]"`, qui installe hypercorn) et `openssl`.

| Fonctionnalité | Ce qu'elle vérifie | Si elle échoue |
| --- | --- | --- |
| `tests/features/flux_http2.feature` ([#278](https://github.com/dascritch/machincast/issues/278)) | Un serveur local sert un flux AAC en HTTP/2, chiffré, qui gèle au bout de 3 secondes. Lu comme le lit MachinCast, il est servi en HTTP/1.1, et le lecteur le signale en erreur au plus 15 secondes après le gel. Lu en HTTP/2, le lecteur ne signale rien, mais la garde de MachinCast voit la voie gelée. | Sur « servi en HTTP/1.1 » ou « en erreur » : `SOUP_FORCE_HTTP1` n'a plus d'effet, la panne ci-dessus peut revenir. Sur « toujours en cours » en HTTP/2 : libsoup signale désormais le gel en HTTP/2, et le passage forcé en HTTP/1.1 peut être reconsidéré, dans un ticket. |
