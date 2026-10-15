-- Annulation du schéma initial (https://github.com/dascritch/machincast/pull/70).
-- Les rôles ne sont pas supprimés : ils appartiennent au serveur et servent aussi à l'autre base.

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM machincast_lecture, machincast_indexation, machincast_interface;
REVOKE USAGE ON SCHEMA public FROM machincast_lecture, machincast_indexation, machincast_interface;

DROP TABLE log;
DROP TABLE airplay;
DROP TABLE evenements_elements;
DROP TABLE evenements;
DROP TABLE banques_sonores;
DROP TABLE banques_repertoires;
DROP TABLE banques;
DROP TABLE sonores;
DROP TABLE marques_pages_streams;
DROP FUNCTION machincast_maj_modifie_le();
DROP TYPE etat_sonore;
DROP TYPE niveau_log;
DROP TYPE type_ligne_airplay;
DROP TYPE jour_semaine;
DROP TYPE priorite_evenement;
DROP TYPE mode_banque;
DROP TYPE type_sonore;
