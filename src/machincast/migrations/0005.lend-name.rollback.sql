-- Annulation du prêt de nom (https://github.com/dascritch/machincast/issues/399). PostgreSQL ne retire pas une valeur
-- d'un type énuméré : le type est recréé sans elle, et un événement qui prêtait son nom rejoue de nouveau sa liste.

ALTER TABLE airplay DROP COLUMN lender_event_id;

UPDATE events SET end_of_list = 'replay' WHERE end_of_list = 'lend_name';
ALTER TABLE events DROP CONSTRAINT events_end_of_list, ALTER COLUMN end_of_list DROP DEFAULT;
ALTER TYPE end_of_list RENAME TO end_of_list_0005;
CREATE TYPE end_of_list AS ENUM ('replay', 'background_programming', 'fallback');
ALTER TABLE events
	ALTER COLUMN end_of_list TYPE end_of_list USING end_of_list::text::end_of_list,
	ALTER COLUMN end_of_list SET DEFAULT 'replay',
	ADD CONSTRAINT events_end_of_list
		CHECK (end_of_list = 'replay' OR (ends_at IS NOT NULL AND priority IN ('show', 'special')));
DROP TYPE end_of_list_0005;
