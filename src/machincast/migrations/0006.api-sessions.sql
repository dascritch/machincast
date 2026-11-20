-- Les sessions de l'intranet et de l'API (https://github.com/dascritch/machincast/issues/539).
-- Une connexion par nom et mot de passe ouvre une session à valider (pending), avec un code à 6 chiffres que montre
-- l'interface, au pupitre ; le code saisi sur le poste distant la rend valide jusqu'à expires_at. Un délai dépassé,
-- trop de codes faux, une déconnexion ou une invalidation au pupitre la rendent invalide. Le cookie de session n'est
-- gardé que par son empreinte SHA-256.

CREATE TYPE api_session_state AS ENUM ('pending', 'valid', 'invalid');
-- intranet : ouverte par la mire de connexion ; interface : générée au pupitre, pour l'API.
CREATE TYPE api_session_origin AS ENUM ('intranet', 'interface');

CREATE TABLE api_sessions (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	user_id bigint NOT NULL REFERENCES api_users (id) ON DELETE CASCADE,
	token_hash text NOT NULL UNIQUE CHECK (token_hash ~ '^[0-9a-f]{64}$'),
	origin api_session_origin NOT NULL DEFAULT 'intranet',
	state api_session_state NOT NULL DEFAULT 'pending',
	-- Le code à donner au poste distant, tant que la session est à valider.
	code char(6) CHECK (code ~ '^[0-9]{6}$'),
	attempts smallint NOT NULL DEFAULT 0 CHECK (attempts >= 0),
	user_agent text,
	source_ip inet,
	created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
	validate_before timestamptz,
	validated_at timestamptz,
	expires_at timestamptz,
	ended_at timestamptz,
	CHECK ((state <> 'pending') OR ((code IS NOT NULL) AND (validate_before IS NOT NULL))),
	CHECK ((state <> 'valid') OR ((code IS NULL) AND (expires_at IS NOT NULL)))
);

CREATE INDEX api_sessions_user ON api_sessions (user_id);
CREATE INDEX api_sessions_pending ON api_sessions (state) WHERE state = 'pending';

GRANT SELECT, INSERT, UPDATE ON api_sessions TO machincast_interface, machincast_intranet;
