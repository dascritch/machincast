# Règles — Interface graphique

À lire avant de toucher à `Machin_interface`. Écrans complets : [spec.md § 8](../spec.md#8-interface-graphique).

- PySide6, version alignée sur Qt 6.10 (Kubuntu 26.04 LTS).
- Vocabulaire à l'écran : « banque », jamais « playlist ».
- Les champs de texte courts (noms, artiste, titre) sont limités à `LONGUEUR_TEXTE_COURT` (255 caractères), comme en base.
- L'état du binaire lecture se lit par sa socket Unix, jamais en interrogeant `airplay` en boucle.
- Le service se pilote via systemd et polkit, jamais par sudo.
- La pré-écoute utilise obligatoirement un autre périphérique de sortie que le binaire lecture.
- Un fichier ajouté à la main est enregistré à l'état `apercu` : l'indexeur le décodera ; un stream est enregistré `actif` ([#69](https://github.com/dascritch/machincast/issues/69)).
- Tout champ d'un sonore saisi à la main est ajouté à `sonores.champs_edites` : son nom de colonne, ou `metadonnees_musicales.<clé>` pour une clé des métadonnées musicales.
- Refuser à la saisie le chevauchement de deux événements de même priorité.
- À l'édition d'un événement, prévenir quand une banque « ne pas répéter » occupe deux lignes contiguës, y compris la dernière et la première d'un événement qui boucle : `machincast.lecture.deroule.appels_ignores` donne les lignes qui seront sautées. L'avertissement n'empêche pas d'enregistrer ([#63](https://github.com/dascritch/machincast/issues/63), [#32](https://github.com/dascritch/machincast/issues/32)).
- Toute suppression d'un élément référencé ailleurs passe par une validation qui liste les références.
- Supprimer un sonore supprime sa ligne en base, jamais son fichier ([#96](https://github.com/dascritch/machincast/issues/96)) : l'interface ne supprime, ne renomme, ne déplace ni n'écrit aucun fichier sonore. Voir [developpement.md](developpement.md#fichiers-sonores).
- Les listes d'une banque séquentielle et d'un événement se réordonnent par glisser-déposer.
- Si aucun fil musical n'existe, en recréer un.
- Prévoir l'absence de VU-mètre (sortie ALSA) et l'absence de durée (streams).
- Un stream propose son événement de secours parmi les seuls événements de priorité `secours`, ou aucun (le fil musical) ; un événement de secours ne se saisit ni avec des dates, ni avec des jours, et n'apparaît pas dans la vue calendrier ([#16](https://github.com/dascritch/machincast/issues/16)).
