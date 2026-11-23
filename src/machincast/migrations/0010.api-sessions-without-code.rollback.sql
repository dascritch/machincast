-- Annulation des connexions validées au pupitre sans code (https://github.com/dascritch/machincast/issues/600) :
-- celles qui attendent encore ne se valideront plus.

UPDATE api_sessions SET state = 'invalid', ended_at = clock_timestamp() WHERE state = 'pending' AND code IS NULL;
ALTER TABLE api_sessions DROP CONSTRAINT api_sessions_pending_delay;
ALTER TABLE api_sessions ADD CONSTRAINT api_sessions_check
	CHECK ((state <> 'pending') OR ((code IS NOT NULL) AND (validate_before IS NOT NULL)));
