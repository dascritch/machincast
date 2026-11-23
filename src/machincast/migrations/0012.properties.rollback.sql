-- Annulation de la colonne properties (https://github.com/dascritch/machincast/issues/607) : les secours d'un
-- événement redeviennent des colonnes, clés étrangères ; les autres propriétés, celles des plugins comprises,
-- sont perdues.

DROP TRIGGER events_forget_fallback ON events;
DROP FUNCTION machincast_forget_event_fallback();
DROP TRIGGER events_fallbacks ON events;
DROP INDEX events_end_fallback;
DROP INDEX events_stream_fallback;
ALTER TABLE events DROP CONSTRAINT events_fallbacks_identifiers;

ALTER TABLE events ADD COLUMN end_fallback_event_id bigint REFERENCES events (id) ON DELETE SET NULL;
ALTER TABLE events ADD COLUMN stream_fallback_event_id bigint REFERENCES events (id) ON DELETE SET NULL;
UPDATE events SET end_fallback_event_id = (properties ->> 'end_fallback_event')::bigint,
	stream_fallback_event_id = (properties ->> 'stream_fallback_event')::bigint;
CREATE INDEX events_end_fallback ON events (end_fallback_event_id);
CREATE INDEX events_stream_fallback ON events (stream_fallback_event_id);

CREATE OR REPLACE FUNCTION machincast_check_event_fallbacks() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
	IF NEW.end_fallback_event_id IS NOT NULL THEN
		IF NOT EXISTS (SELECT 1 FROM events WHERE id = NEW.end_fallback_event_id AND priority = 'fallback') THEN
			RAISE EXCEPTION 'l''événement % n''est pas un événement de secours', NEW.end_fallback_event_id
				USING ERRCODE = 'check_violation';
		END IF;
	END IF;
	IF NEW.stream_fallback_event_id IS NOT NULL THEN
		IF NOT EXISTS (SELECT 1 FROM events WHERE id = NEW.stream_fallback_event_id AND priority = 'fallback') THEN
			RAISE EXCEPTION 'l''événement % n''est pas un événement de secours', NEW.stream_fallback_event_id
				USING ERRCODE = 'check_violation';
		END IF;
	END IF;
	RETURN NEW;
END;
$$;

CREATE TRIGGER events_fallbacks BEFORE INSERT OR UPDATE OF end_fallback_event_id, stream_fallback_event_id ON events
	FOR EACH ROW EXECUTE FUNCTION machincast_check_event_fallbacks();

CREATE OR REPLACE FUNCTION machincast_check_event_fallback() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
	IF OLD.priority = 'fallback' AND NEW.priority <> 'fallback' THEN
		IF EXISTS (SELECT 1 FROM sounds WHERE fallback_event_id = NEW.id) THEN
			RAISE EXCEPTION 'l''événement % sert de secours à un stream : il reste de priorité secours', NEW.id
				USING ERRCODE = 'check_violation';
		END IF;
		IF EXISTS (SELECT 1 FROM events WHERE end_fallback_event_id = NEW.id OR stream_fallback_event_id = NEW.id) THEN
			RAISE EXCEPTION 'l''événement % sert de secours à un événement : il reste de priorité secours', NEW.id
				USING ERRCODE = 'check_violation';
		END IF;
	END IF;
	RETURN NEW;
END;
$$;

ALTER TABLE events DROP COLUMN properties;
ALTER TABLE banks DROP COLUMN properties;
ALTER TABLE sounds DROP COLUMN properties;
ALTER TABLE sequences DROP COLUMN properties;
ALTER TABLE feeds DROP COLUMN properties;
ALTER TABLE api_users DROP COLUMN properties;
ALTER TABLE api_sessions DROP COLUMN properties;
