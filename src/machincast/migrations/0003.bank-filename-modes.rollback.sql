-- Annulation des modes de banque dans l'ordre du nom de fichier (https://github.com/dascritch/machincast/issues/454) :
-- une valeur ne se retire pas d'un type énuméré, qui est donc recréé ; ces banques passent en mode séquentiel.

ALTER TYPE bank_mode RENAME TO bank_mode_with_filename;
CREATE TYPE bank_mode AS ENUM ('sequential', 'random');
ALTER TABLE banks ALTER COLUMN mode TYPE bank_mode USING (
	CASE WHEN mode::text IN ('filename_ascending', 'filename_descending') THEN 'sequential' ELSE mode::text END
)::bank_mode;
DROP TYPE bank_mode_with_filename;
