# Dépannage

Les pannes connues de MachinCast, leurs causes, ce qu'il faut vérifier, et les scénarios qui les surveillent. Les messages du journal se lisent par `Machin logs` (la diffusion), ou dans l'onglet **Incidents** de l'interface.

## Un stream tombe, mais l'antenne reste en silence

**Symptôme** : un stream tombe, par exemple quand le réseau est coupé. L'antenne reste en silence, sans repli sur l'événement de secours ni sur le fil musical, et le journal ne note aucun `flux tombé`. Quand le réseau revient, le stream ne reprend pas : il faut relancer la diffusion.

**Cause** ([#278](https://github.com/dascritch/machincast/issues/278)) : le flux est servi en **HTTP/2**, souvent derrière un serveur nginx, comme celui de France Inter. En HTTP/2, libsoup 3, la bibliothèque par laquelle GStreamer lit les streams, ne signale pas qu'une connexion ne donne plus rien ([ticket 256 de libsoup](https://gitlab.gnome.org/GNOME/libsoup/-/issues/256), [ticket 367 de libsoup](https://gitlab.gnome.org/GNOME/libsoup/-/issues/367), [ticket 296 de libsoup](https://gitlab.gnome.org/GNOME/libsoup/-/issues/296)) : le lecteur attend sans fin, sans erreur. Un flux servi en HTTP/1.1, comme un Icecast direct, n'est pas touché. Le type du flux (MP3, AAC) n'y est pour rien. Un autre lecteur bâti sur GStreamer a contourné le même défaut de la même façon ([ticket 252 de sone](https://github.com/lullabyX/sone/issues/252)).

**Ce que fait MachinCast** :

- Il lit tous ses flux en HTTP/1.1 : la variable `SOUP_FORCE_HTTP1` est posée au lancement de chacun de ses programmes. Le délai de 10 secondes de la connexion s'applique alors, et le lecteur signale le flux tombé.
- Il tient aussi pour tombé un stream dont la lecture n'avance plus pendant **10 secondes**, le même délai de garde que pour une lecture bloquée et pour la connexion d'un flux en HTTP/1.1, même si le lecteur ne signale rien. Le journal note alors `flux tombé` : « plus de son depuis 10 secondes, sans erreur du lecteur ».
- La reconnexion reprend le stream dès que du son revient.

**À vérifier** :

- La version de HTTP d'un flux : `curl -I <adresse>`. La première ligne dit `HTTP/2 200` ou `HTTP/1.1 200`.
- Le journal pendant la panne : `Machin logs`. Un `flux tombé` doit apparaître une dizaine de secondes après la coupure, un peu plus si le lecteur avait du son d'avance, puis `reprise du flux` après son retour.
- Si l'antenne reste encore en silence sans `flux tombé`, ouvrir un ticket avec le journal, l'adresse du flux et la réponse de `curl -I`.

## Scénarios à lancer avant une version

Certains scénarios ne tournent ni avec `pytest`, ni avec `bin/Machin dev-test` : ils sont lents, ou ont besoin d'un serveur à part. Ils sont marqués `@release`, et se lancent avant chaque version ([#208](https://github.com/dascritch/machincast/issues/208)), et après toute mise à jour de GStreamer ou de libsoup :

```bash
.venv/bin/pytest -m release
```

Ils demandent les dépendances de test (`./install.sh --dev`, ou `pip install --editable ".[dev]"`, qui installe hypercorn) et `openssl`.

| Fonctionnalité | Ce qu'elle vérifie | Si elle échoue |
| --- | --- | --- |
| `tests/features/flux_http2.feature` ([#278](https://github.com/dascritch/machincast/issues/278)) | Un serveur local sert un flux AAC en HTTP/2, chiffré, qui gèle au bout de 3 secondes. Lu comme le lit MachinCast, il est servi en HTTP/1.1, et le lecteur le signale en erreur au plus 15 secondes après le gel. Lu en HTTP/2, le lecteur ne signale rien, mais la garde de MachinCast voit la voie gelée. | Sur « servi en HTTP/1.1 » ou « en erreur » : `SOUP_FORCE_HTTP1` n'a plus d'effet, la panne ci-dessus peut revenir. Sur « toujours en cours » en HTTP/2 : libsoup signale désormais le gel en HTTP/2, et le passage forcé en HTTP/1.1 peut être reconsidéré, dans un ticket. |
