-- La date du dernier parcours de chaque répertoire de banque par l'indexeur
-- (https://github.com/dascritch/machincast/issues/392) : le statut des indexations compte les répertoires parcourus
-- depuis le dernier démarrage de Machin_indexer.

ALTER TABLE bank_directories ADD COLUMN scanned_at timestamptz;

COMMENT ON COLUMN bank_directories.scanned_at IS 'Fin du dernier parcours complet du répertoire par l''indexeur ; NULL jamais parcouru.';

GRANT UPDATE (scanned_at) ON bank_directories TO machincast_indexer;
