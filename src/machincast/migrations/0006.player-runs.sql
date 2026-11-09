-- Démarrages, fins et plantages probables de Machin player dans le log, comme les autres binaires
-- (https://github.com/dascritch/machincast/issues/342, suite de https://github.com/dascritch/machincast/issues/341).
-- Référence : doc/fr/spec.md § 3.2 (rôles et droits) et § 5.2 (log).
--
-- Le rôle de la lecture écrit déjà le log ; il peut maintenant retrouver son démarrage précédent, sans lire le log :
-- machincast_previous_start ne rend que l'heure, le pid et la fin de ce démarrage.
-- depends: 0005.lend-name

GRANT EXECUTE ON FUNCTION machincast_previous_start(text) TO machincast_player;
