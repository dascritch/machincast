-- Annulation des droits (https://github.com/dascritch/machincast/issues/4).
-- Les rôles ne sont pas supprimés : ils appartiennent au serveur et servent aussi à l'autre base.

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM machincast_lecture, machincast_indexation, machincast_interface;
REVOKE USAGE ON SCHEMA public FROM machincast_lecture, machincast_indexation, machincast_interface;
