-- Annulation de la date de parcours des répertoires de banque (https://github.com/dascritch/machincast/issues/392).

REVOKE UPDATE (scanned_at) ON bank_directories FROM machincast_indexer;
ALTER TABLE bank_directories DROP COLUMN scanned_at;
