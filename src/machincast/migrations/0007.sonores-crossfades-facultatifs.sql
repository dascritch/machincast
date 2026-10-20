-- Crossfades facultatifs d'un sonore (https://github.com/dascritch/machincast/issues/145) : NULL n'est pas paramétré, et
-- prend celui de la banque ou de la configuration ; 0 seconde est un crossfade paramétré. Un 0 seconde que personne n'a
-- saisi dans la fiche du sonore (absent de champs_edites) n'était qu'une valeur par défaut : il devient NULL.
-- depends: 0006.banques-durees

ALTER TABLE sonores
	ALTER COLUMN crossfade_debut DROP NOT NULL,
	ALTER COLUMN crossfade_debut DROP DEFAULT,
	ALTER COLUMN crossfade_fin DROP NOT NULL,
	ALTER COLUMN crossfade_fin DROP DEFAULT;

UPDATE sonores SET crossfade_debut = NULL WHERE NOT ('crossfade_debut' = ANY (champs_edites));
UPDATE sonores SET crossfade_fin = NULL WHERE NOT ('crossfade_fin' = ANY (champs_edites));

COMMENT ON COLUMN sonores.crossfade_debut IS 'Crossfade de début ; NULL s''il n''est pas paramétré, 0 seconde en est un.';
COMMENT ON COLUMN sonores.crossfade_fin IS 'Crossfade de fin ; NULL s''il n''est pas paramétré, 0 seconde en est un.';
