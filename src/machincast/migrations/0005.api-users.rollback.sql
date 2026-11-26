-- Annulation des comptes de l'intranet et de l'API (https://github.com/dascritch/machincast/issues/537). Le rôle
-- machincast_webserver reste, comme les autres rôles : il appartient au serveur.

DROP TABLE api_users;
DROP TYPE api_role;
REVOKE USAGE ON SCHEMA public FROM machincast_webserver;
