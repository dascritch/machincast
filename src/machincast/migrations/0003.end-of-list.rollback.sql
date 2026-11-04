-- Annulation de la fin de liste et des secours d'un événement (https://github.com/dascritch/machincast/issues/350).

CREATE OR REPLACE FUNCTION machincast_check_event_fallback() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
	IF OLD.priority = 'fallback' AND NEW.priority <> 'fallback' THEN
		IF EXISTS (SELECT 1 FROM sounds WHERE fallback_event_id = NEW.id) THEN
			RAISE EXCEPTION 'l''événement % sert de secours à un stream : il reste de priorité secours', NEW.id
				USING ERRCODE = 'check_violation';
		END IF;
	END IF;
	RETURN NEW;
END;
$$;

DROP TRIGGER events_fallbacks ON events;
DROP FUNCTION machincast_check_event_fallbacks();
ALTER TABLE events
	DROP CONSTRAINT events_end_of_list,
	DROP COLUMN stream_fallback_event_id,
	DROP COLUMN end_fallback_event_id,
	DROP COLUMN end_of_list;
DROP TYPE end_of_list;
