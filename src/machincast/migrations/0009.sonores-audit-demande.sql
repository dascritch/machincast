-- Audit complet demandé (https://github.com/dascritch/machincast/issues/114). L'interface marque des sonores ; la
-- prochaine indexation, même rapide, les décode et mesure leurs blancs comme l'audit complet, puis efface la marque.
-- depends: 0008.detection-blancs

ALTER TABLE sonores ADD COLUMN audit_demande boolean NOT NULL DEFAULT false;
COMMENT ON COLUMN sonores.audit_demande IS 'La prochaine indexation, même rapide, fait l''audit complet du sonore.';
