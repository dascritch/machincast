-- Le second facteur de l'intranet, et les navigateurs connus (https://github.com/dascritch/machincast/issues/601).
-- La première connexion d'un navigateur passe intranet.first_login ; une fois sa session valide, il est retenu, par un
-- cookie dont la base ne garde que l'empreinte, et ne la repasse plus. Chaque connexion passe ensuite le second
-- facteur : aucun, le code de l'application d'authentification du compte, ou le pupitre.

-- La clé de l'application d'authentification d'un compte, en base32 : réglée par l'interface, lue par l'intranet.
ALTER TABLE api_users ADD COLUMN totp_secret text CHECK (totp_secret ~ '^[A-Z2-7]{32}$');

CREATE TABLE api_browsers (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	user_id bigint NOT NULL REFERENCES api_users (id) ON DELETE CASCADE,
	-- L'empreinte SHA-256 du cookie du navigateur, jamais le cookie lui-même.
	token_hash text NOT NULL UNIQUE CHECK (token_hash ~ '^[0-9a-f]{64}$'),
	user_agent text,
	created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
	used_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX api_browsers_user ON api_browsers (user_id);

-- L'intranet retient un navigateur et note sa dernière connexion ; seule l'interface en oublie.
GRANT SELECT, INSERT ON api_browsers TO machincast_intranet;
GRANT UPDATE (used_at) ON api_browsers TO machincast_intranet;
GRANT SELECT, DELETE ON api_browsers TO machincast_interface;

-- Ce que la session à valider attend encore : l'acceptation au pupitre, puis le code de l'application
-- d'authentification.
ALTER TABLE api_sessions ADD COLUMN desk boolean NOT NULL DEFAULT true;
ALTER TABLE api_sessions ADD COLUMN totp boolean NOT NULL DEFAULT false;
