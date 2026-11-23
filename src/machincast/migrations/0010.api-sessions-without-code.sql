-- Une connexion validée au pupitre, sans code (https://github.com/dascritch/machincast/issues/600).
-- La sécurité de la première connexion se règle : intranet.first_login à « desk », la session à valider n'a pas de
-- code ; le pupitre l'accepte, et le navigateur entre de lui-même. Une session à valider garde son délai.

ALTER TABLE api_sessions DROP CONSTRAINT api_sessions_check;
ALTER TABLE api_sessions ADD CONSTRAINT api_sessions_pending_delay
	CHECK ((state <> 'pending') OR (validate_before IS NOT NULL));
