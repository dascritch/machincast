-- Les comptes de l'intranet et de l'API (https://github.com/dascritch/machincast/issues/537), que gère l'onglet « API »
-- de l'interface, et le rôle du serveur intranet, Machin_intranet, qui ne fait que les lire.
-- Le rôle appartient au serveur : install.sh le crée d'abord, cette migration seulement s'il manque.

DO $$
BEGIN
	IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'machincast_intranet') THEN
		CREATE ROLE machincast_intranet NOLOGIN;
	END IF;
END;
$$;

GRANT USAGE ON SCHEMA public TO machincast_intranet;

-- consult : l'intranet et l'API en lecture ; actions : de même, et les actions de l'API à venir.
CREATE TYPE api_role AS ENUM ('consult', 'actions');

CREATE TABLE api_users (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	-- Le nom se tape dans une adresse, https://nom@adresse : lettres sans accent, chiffres, point, tiret, souligné.
	name varchar(255) NOT NULL UNIQUE CHECK (name ~ '^[A-Za-z0-9._-]+$'),
	-- Empreinte scrypt salée (machincast.shared.passwords), jamais le mot de passe.
	password_hash text NOT NULL CHECK (password_hash LIKE 'scrypt$%'),
	role api_role NOT NULL DEFAULT 'consult',
	disabled_at timestamptz,
	created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
	modified_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TRIGGER api_users_modified_at BEFORE UPDATE ON api_users
	FOR EACH ROW EXECUTE FUNCTION machincast_set_modified_at();

GRANT SELECT, INSERT, UPDATE, DELETE ON api_users TO machincast_interface;
GRANT SELECT ON api_users TO machincast_intranet;
