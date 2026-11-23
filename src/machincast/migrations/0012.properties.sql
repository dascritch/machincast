-- Une colonne JSON, properties, pour les propriétés propres à un élément, sans étendre le schéma
-- (https://github.com/dascritch/machincast/issues/607, ticket enfant de
-- https://github.com/dascritch/machincast/issues/606). Toujours un objet ; un plugin range les siennes sous son nom.
-- Les secours d'un événement y migrent, sous end_fallback_event et stream_fallback_event : des déclencheurs gardent
-- ce que garantissaient leurs clés étrangères.

ALTER TABLE events ADD COLUMN properties jsonb NOT NULL DEFAULT '{}'
	CONSTRAINT events_properties_object CHECK (jsonb_typeof(properties) = 'object');
ALTER TABLE banks ADD COLUMN properties jsonb NOT NULL DEFAULT '{}'
	CONSTRAINT banks_properties_object CHECK (jsonb_typeof(properties) = 'object');
ALTER TABLE sounds ADD COLUMN properties jsonb NOT NULL DEFAULT '{}'
	CONSTRAINT sounds_properties_object CHECK (jsonb_typeof(properties) = 'object');
ALTER TABLE sequences ADD COLUMN properties jsonb NOT NULL DEFAULT '{}'
	CONSTRAINT sequences_properties_object CHECK (jsonb_typeof(properties) = 'object');
ALTER TABLE feeds ADD COLUMN properties jsonb NOT NULL DEFAULT '{}'
	CONSTRAINT feeds_properties_object CHECK (jsonb_typeof(properties) = 'object');
ALTER TABLE api_users ADD COLUMN properties jsonb NOT NULL DEFAULT '{}'
	CONSTRAINT api_users_properties_object CHECK (jsonb_typeof(properties) = 'object');
ALTER TABLE api_sessions ADD COLUMN properties jsonb NOT NULL DEFAULT '{}'
	CONSTRAINT api_sessions_properties_object CHECK (jsonb_typeof(properties) = 'object');

-- ─── Les secours d'un événement, dans properties ───────────

DROP TRIGGER events_fallbacks ON events;
UPDATE events SET properties = jsonb_strip_nulls(
	jsonb_build_object('end_fallback_event', end_fallback_event_id, 'stream_fallback_event', stream_fallback_event_id)
);
ALTER TABLE events DROP COLUMN end_fallback_event_id;
ALTER TABLE events DROP COLUMN stream_fallback_event_id;

-- Un secours désigné est un identifiant d'événement, un nombre entier.
ALTER TABLE events ADD CONSTRAINT events_fallbacks_identifiers CHECK (
	(jsonb_typeof(properties -> 'end_fallback_event') IS NULL
		OR jsonb_typeof(properties -> 'end_fallback_event') = 'number')
	AND (jsonb_typeof(properties -> 'stream_fallback_event') IS NULL
		OR jsonb_typeof(properties -> 'stream_fallback_event') = 'number')
);

CREATE INDEX events_end_fallback ON events (((properties ->> 'end_fallback_event')::bigint));
CREATE INDEX events_stream_fallback ON events (((properties ->> 'stream_fallback_event')::bigint));

-- Les secours qu'un événement désigne existent, et sont des événements de priorité fallback
-- (https://github.com/dascritch/machincast/issues/350).
CREATE OR REPLACE FUNCTION machincast_check_event_fallbacks() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
	designated bigint;
BEGIN
	FOREACH designated IN ARRAY ARRAY[
		(NEW.properties ->> 'end_fallback_event')::bigint, (NEW.properties ->> 'stream_fallback_event')::bigint
	] LOOP
		IF designated IS NOT NULL
			AND NOT EXISTS (SELECT 1 FROM events WHERE id = designated AND priority = 'fallback') THEN
			RAISE EXCEPTION 'l''événement % n''est pas un événement de secours', designated
				USING ERRCODE = 'check_violation';
		END IF;
	END LOOP;
	RETURN NEW;
END;
$$;

CREATE TRIGGER events_fallbacks BEFORE INSERT OR UPDATE OF properties ON events
	FOR EACH ROW EXECUTE FUNCTION machincast_check_event_fallbacks();

-- Un événement qui sert de secours reste de priorité secours.
CREATE OR REPLACE FUNCTION machincast_check_event_fallback() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
	IF OLD.priority = 'fallback' AND NEW.priority <> 'fallback' THEN
		IF EXISTS (SELECT 1 FROM sounds WHERE fallback_event_id = NEW.id) THEN
			RAISE EXCEPTION 'l''événement % sert de secours à un stream : il reste de priorité secours', NEW.id
				USING ERRCODE = 'check_violation';
		END IF;
		IF EXISTS (
			SELECT 1 FROM events WHERE (properties ->> 'end_fallback_event')::bigint = NEW.id
				OR (properties ->> 'stream_fallback_event')::bigint = NEW.id
		) THEN
			RAISE EXCEPTION 'l''événement % sert de secours à un événement : il reste de priorité secours', NEW.id
				USING ERRCODE = 'check_violation';
		END IF;
	END IF;
	RETURN NEW;
END;
$$;

-- Supprimer un événement de secours laisse sans secours les événements qui le désignaient, comme le faisait
-- ON DELETE SET NULL.
-- SECURITY DEFINER : avec les droits du propriétaire des tables, quel que soit le rôle qui supprime.
CREATE FUNCTION machincast_forget_event_fallback() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
BEGIN
	UPDATE events SET properties = properties - 'end_fallback_event'
		WHERE (properties ->> 'end_fallback_event')::bigint = OLD.id;
	UPDATE events SET properties = properties - 'stream_fallback_event'
		WHERE (properties ->> 'stream_fallback_event')::bigint = OLD.id;
	RETURN OLD;
END;
$$;

CREATE TRIGGER events_forget_fallback AFTER DELETE ON events
	FOR EACH ROW EXECUTE FUNCTION machincast_forget_event_fallback();
