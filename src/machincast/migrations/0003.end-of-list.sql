-- Fin de liste et secours d'un événement (https://github.com/dascritch/machincast/issues/350). Référence :
-- doc/fr/spec.md § 3.1 (events) et § 4.3 (liste de lecture).
--
-- Une émission ou un spécial qui a une fin choisit ce qui suit la fin de sa liste, avant la fin de son occurrence :
-- la rejouer (replay, comme avant), laisser l'antenne au fil musical en dessous (background_programming), ou passer à
-- son secours de fin de liste (fallback, end_fallback_event_id). Un événement choisit aussi le secours d'un stream de
-- sa liste qui tombe (stream_fallback_event_id), qui l'emporte sur celui du stream. Un secours est toujours un
-- événement de priorité fallback.
-- depends: 0002.run-log

CREATE TYPE end_of_list AS ENUM ('replay', 'background_programming', 'fallback');

ALTER TABLE events
	ADD COLUMN end_of_list end_of_list NOT NULL DEFAULT 'replay',
	ADD COLUMN end_fallback_event_id bigint REFERENCES events (id) ON DELETE SET NULL,
	ADD COLUMN stream_fallback_event_id bigint REFERENCES events (id) ON DELETE SET NULL,
	-- Sans fin, la liste ne boucle pas : rien à choisir. Un fil musical et un secours rejouent toujours leur liste.
	ADD CONSTRAINT events_end_of_list
		CHECK (end_of_list = 'replay' OR (ends_at IS NOT NULL AND priority IN ('show', 'special')));

CREATE INDEX events_end_fallback ON events (end_fallback_event_id);
CREATE INDEX events_stream_fallback ON events (stream_fallback_event_id);

-- Les secours d'un événement sont des événements de priorité fallback : vérifié à l'enregistrement de l'événement.
-- Conditions imbriquées, comme pour le secours d'un stream : la requête n'est préparée que si elle est nécessaire.
CREATE FUNCTION machincast_check_event_fallbacks() RETURNS trigger
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

-- Un secours désigné, par un stream ou par un événement, garde sa priorité.
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
