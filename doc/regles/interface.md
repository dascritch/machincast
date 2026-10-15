# Règles — Interface graphique

À lire avant de toucher à `Machin_interface`. Écrans complets : [spec.md § 8](../spec.md#8-interface-graphique).

- PySide6, version alignée sur Qt 6.10 (Kubuntu 26.04 LTS).
- Vocabulaire à l'écran : « banque », jamais « playlist ».
- Les champs de texte courts (noms, artiste, titre) sont limités à `LONGUEUR_TEXTE_COURT` (255 caractères), comme en base.
- L'état du binaire lecture se lit par sa socket Unix, jamais en interrogeant `airplay` en boucle.
- Le service se pilote via systemd et polkit, jamais par sudo.
- La pré-écoute utilise obligatoirement un autre périphérique de sortie que le binaire lecture.
- Tout champ d'un sonore saisi à la main est ajouté à `sonores.champs_edites` : son nom de colonne, ou `metadonnees_musicales.<clé>` pour une clé des métadonnées musicales.
- Refuser à la saisie le chevauchement de deux événements de même priorité.
- Toute suppression d'un élément référencé ailleurs passe par une validation qui liste les références.
- Les listes d'une banque séquentielle et d'un événement se réordonnent par glisser-déposer.
- Si aucun fil musical n'existe, en recréer un.
- Prévoir l'absence de VU-mètre (sortie ALSA) et l'absence de durée (streams).
