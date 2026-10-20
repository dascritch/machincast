-- Annulation des crossfades facultatifs d'un sonore (https://github.com/dascritch/machincast/issues/145) : un crossfade
-- non paramétré redevient 0 seconde.

UPDATE sonores SET crossfade_debut = '0 s' WHERE crossfade_debut IS NULL;
UPDATE sonores SET crossfade_fin = '0 s' WHERE crossfade_fin IS NULL;

ALTER TABLE sonores
	ALTER COLUMN crossfade_debut SET DEFAULT '0 s',
	ALTER COLUMN crossfade_debut SET NOT NULL,
	ALTER COLUMN crossfade_fin SET DEFAULT '0 s',
	ALTER COLUMN crossfade_fin SET NOT NULL;
