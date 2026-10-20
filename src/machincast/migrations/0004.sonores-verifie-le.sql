-- Date de la dernière vérification complète du fichier d'un sonore, par l'indexeur : son type lu, puis son décodage
-- (https://github.com/dascritch/machincast/issues/125).
-- depends: 0003.sonores-type-de-fichier

ALTER TABLE sonores ADD COLUMN verifie_le timestamptz;
COMMENT ON COLUMN sonores.verifie_le IS 'Dernière vérification complète du fichier par l''indexeur ; NULL avant.';
