-- Annulation de la priorité « imprévu » (https://github.com/dascritch/machincast/issues/402). PostgreSQL ne retire pas
-- une valeur d'un type énuméré : le type est recréé sans elle, et un imprévu devient un spécial.

-- Les contraintes qui comparent la priorité à une valeur la comparent au type : elles sont recréées après.
ALTER TABLE events
	DROP CONSTRAINT events_breaking_once,
	DROP CONSTRAINT events_end_of_list,
	DROP CONSTRAINT events_start,
	DROP CONSTRAINT events_fallback_off_grid;
UPDATE events SET priority = 'special' WHERE priority = 'breaking';
-- Une colonne qu'un déclencheur nomme ne change pas de type : le déclencheur est recréé après.
DROP TRIGGER events_fallback ON events;
ALTER TYPE event_priority RENAME TO event_priority_0007;
CREATE TYPE event_priority AS ENUM ('fallback', 'background_programming', 'show', 'special');
ALTER TABLE events
	ALTER COLUMN priority TYPE event_priority USING priority::text::event_priority,
	ADD CONSTRAINT events_end_of_list
		CHECK (end_of_list = 'replay' OR (ends_at IS NOT NULL AND priority IN ('show', 'special'))),
	ADD CONSTRAINT events_start CHECK (starts_at IS NOT NULL OR priority IN ('background_programming', 'fallback')),
	ADD CONSTRAINT events_fallback_off_grid
		CHECK (priority <> 'fallback' OR (starts_at IS NULL AND ends_at IS NULL AND recurrence_days = '{}'));
DROP TYPE event_priority_0007;
CREATE TRIGGER events_fallback BEFORE UPDATE OF priority ON events
	FOR EACH ROW EXECUTE FUNCTION machincast_check_event_fallback();
