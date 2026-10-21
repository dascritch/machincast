-- Audit complet optimisé (https://github.com/dascritch/machincast/issues/206) : chaque sonore garde la date de son
-- dernier audit complet et le seuil de blanc auquel il a eu lieu. Un audit complet ne redécode pas un sonore déjà
-- audité au même seuil, dont le fichier n'a pas changé depuis.
-- depends: 0010.indexation-retire-des-banques

ALTER TABLE sonores
	ADD COLUMN audite_le timestamptz,
	ADD COLUMN audit_seuil double precision CHECK (audit_seuil >= -100 AND audit_seuil < 0),
	ADD CONSTRAINT sonores_audit CHECK ((audite_le IS NULL) = (audit_seuil IS NULL));

COMMENT ON COLUMN sonores.audite_le IS 'Date du dernier audit complet du fichier, blancs mesurés ; NULL jamais audité.';
COMMENT ON COLUMN sonores.audit_seuil IS 'Seuil de blanc, en dB crête, du dernier audit complet ; NULL jamais audité.';
