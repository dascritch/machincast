-- Annulation de l'ordre ascendant du tableau des sonores (https://github.com/dascritch/machincast/issues/535) : une
-- valeur ne se retire pas d'un type énuméré, qui est donc recréé ; ces banques passent dans l'ordre descendant du
-- tableau, le mode séquentiel.

ALTER TYPE bank_mode RENAME TO bank_mode_with_table_ascending;
CREATE TYPE bank_mode AS ENUM ('sequential', 'random', 'filename_ascending', 'filename_descending');
ALTER TABLE banks ALTER COLUMN mode TYPE bank_mode USING (
	CASE WHEN mode::text = 'sequential_ascending' THEN 'sequential' ELSE mode::text END
)::bank_mode;
DROP TYPE bank_mode_with_table_ascending;
