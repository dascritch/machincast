-- Annulation des durées des sonores d'une banque (https://github.com/dascritch/machincast/issues/147).

ALTER TABLE banques
	DROP CONSTRAINT banques_durees,
	DROP COLUMN duree_min,
	DROP COLUMN duree_max;
