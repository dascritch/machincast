# Règles — Binaire lecture

À lire avant de toucher à `Machin_lecture`. Comportement complet : [spec.md § 4](../spec.md#4-règles-dordonnancement) et [§ 5](../spec.md#5-binaire-lecture).

## Rôle

Lire les événements et les jouer, rien d'autre. Le binaire tourne comme service systemd.

## Règles à ne jamais enfreindre

- Le début d'un événement coupe **net** le sonore en cours.
- Une banque jouée fait jouer **un seul** sonore.
- Le mode aléatoire est contrôlé : pas de répétition dans une banque avant d'avoir joué tous ses sonores. Le cycle est propre à chaque banque.
- Seuls les sonores jouables sont candidats : actifs, dans leur période de diffusion, sous leur maximum de lectures.
- Artiste et titre sont masqués selon la priorité Événement > Banque > Sonore > configuration. Les sorties privées affichent tout, les sorties publiques appliquent le masquage.
- Jamais de silence non signalé : si rien n'est jouable, émettre un silence et lever une alerte dans le log.

## Écritures autorisées

- `airplay` : une ligne de début et une ligne de fin par passage.
- `log` : toutes les opérations, normales et incidents.
- `sonores.actif` : désactivation au maximum de lectures ou à la fin de la période de diffusion, toujours consignée dans le log.

## Mode simulation

Aucune écriture en base, aucune sortie sonore, état tenu en mémoire, graine reproductible, sorties .csv, .pls et .html nommées à part.

## Interfaces exposées

- Socket Unix d'état pour l'interface graphique.
- Sortie audio GStreamer choisie dans la configuration (ALSA, PulseAudio, PipeWire).
