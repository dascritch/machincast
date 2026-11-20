-- Annulation des sessions de l'intranet et de l'API (https://github.com/dascritch/machincast/issues/539).

DROP TABLE api_sessions;
DROP TYPE api_session_origin;
DROP TYPE api_session_state;
