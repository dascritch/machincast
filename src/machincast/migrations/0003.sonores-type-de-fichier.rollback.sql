-- Annulation du type de fichier (https://github.com/dascritch/machincast/issues/121) : un sonore non supporté redevient
-- erroné, et l'état non_supporte disparaît du type, qu'il faut recréer.

ALTER TABLE sonores DROP COLUMN type_mime;
UPDATE sonores SET etat = 'errone' WHERE etat = 'non_supporte';
ALTER TABLE sonores ALTER COLUMN etat DROP DEFAULT;
ALTER TYPE etat_sonore RENAME TO etat_sonore_avec_non_supporte;
CREATE TYPE etat_sonore AS ENUM ('apercu', 'actif', 'desactive', 'expire', 'errone', 'supprime');
ALTER TABLE sonores ALTER COLUMN etat TYPE etat_sonore USING etat::text::etat_sonore;
ALTER TABLE sonores ALTER COLUMN etat SET DEFAULT 'actif';
DROP TYPE etat_sonore_avec_non_supporte;
