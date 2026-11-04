-- Annulation des démarrages et fins dans le log (https://github.com/dascritch/machincast/issues/341) : les lignes déjà
-- notées restent dans le log.

REVOKE INSERT ON log FROM machincast_indexer;
DROP FUNCTION machincast_previous_start(text);
