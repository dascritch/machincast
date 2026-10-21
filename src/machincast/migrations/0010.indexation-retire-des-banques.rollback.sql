-- Annulation du retrait des sonores hors durées par l'indexation (https://github.com/dascritch/machincast/issues/195).

REVOKE DELETE ON banques_sonores FROM machincast_indexation;
