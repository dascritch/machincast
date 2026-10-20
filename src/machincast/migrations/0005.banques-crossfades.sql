-- Crossfades d'une banque, pour les sonores qu'elle fait jouer : une règle et une durée pour le début, de même pour la
-- fin (https://github.com/dascritch/machincast/issues/143). « sonore » garde le crossfade du sonore, « a_defaut » donne
-- celui de la banque à un sonore qui n'en a pas (0 seconde), « impose » donne celui de la banque à tout sonore.
-- depends: 0004.sonores-verifie-le

CREATE TYPE regle_crossfade AS ENUM ('sonore', 'a_defaut', 'impose');

ALTER TABLE banques
	ADD COLUMN crossfade_debut_regle regle_crossfade NOT NULL DEFAULT 'sonore',
	ADD COLUMN crossfade_debut interval NOT NULL DEFAULT '0 s' CHECK (crossfade_debut >= '0 s'),
	ADD COLUMN crossfade_fin_regle regle_crossfade NOT NULL DEFAULT 'sonore',
	ADD COLUMN crossfade_fin interval NOT NULL DEFAULT '0 s' CHECK (crossfade_fin >= '0 s');

COMMENT ON COLUMN banques.crossfade_debut_regle IS 'Règle du crossfade de début des sonores joués via la banque.';
COMMENT ON COLUMN banques.crossfade_debut IS 'Crossfade de début de la banque, selon sa règle.';
COMMENT ON COLUMN banques.crossfade_fin_regle IS 'Règle du crossfade de fin des sonores joués via la banque.';
COMMENT ON COLUMN banques.crossfade_fin IS 'Crossfade de fin de la banque, selon sa règle.';
