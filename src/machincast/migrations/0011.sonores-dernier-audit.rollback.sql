-- Annulation de l'audit complet optimisé (https://github.com/dascritch/machincast/issues/206).

ALTER TABLE sonores
	DROP CONSTRAINT sonores_audit,
	DROP COLUMN audit_seuil,
	DROP COLUMN audite_le;
