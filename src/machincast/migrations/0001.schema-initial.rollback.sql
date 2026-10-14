-- Annulation du schéma initial (ticket #3).

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
DROP TYPE niveau_log;
DROP TYPE type_ligne_airplay;
DROP TYPE jour_semaine;
DROP TYPE priorite_evenement;
DROP TYPE mode_banque;
DROP TYPE type_sonore;
