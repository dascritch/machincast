-- Annulation de l'acceptation au pupitre (https://github.com/dascritch/machincast/issues/547).

REVOKE UPDATE (state, code, attempts, validated_at, expires_at, ended_at) ON api_sessions FROM machincast_webserver;
GRANT UPDATE ON api_sessions TO machincast_webserver;
ALTER TABLE api_sessions DROP COLUMN accepted_at;
