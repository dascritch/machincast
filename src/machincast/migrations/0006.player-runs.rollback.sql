-- Annulation : le rôle de la lecture ne retrouve plus son démarrage précédent
-- (https://github.com/dascritch/machincast/issues/342).

REVOKE EXECUTE ON FUNCTION machincast_previous_start(text) FROM machincast_player;
