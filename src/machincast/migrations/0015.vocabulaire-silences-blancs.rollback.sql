-- Annulation du vocabulaire des silences et des blancs (https://github.com/dascritch/machincast/issues/291).

UPDATE log SET nature = 'silence' WHERE nature = 'blanc';

COMMENT ON COLUMN sonores.audit_seuil IS 'Seuil de blanc, en dB crête, du dernier audit complet ; NULL jamais audité.';
COMMENT ON COLUMN sonores.audite_le IS 'Date du dernier audit complet du fichier, blancs mesurés ; NULL jamais audité.';
COMMENT ON COLUMN banques.detection_silences IS 'Les sonores joués via la banque le sont sans leurs blancs détectés.';
COMMENT ON COLUMN sonores.detection_silences IS 'Le sonore est joué sans ses blancs détectés, même hors d''une banque qui les retire.';
COMMENT ON COLUMN sonores.fin_detectee IS 'Blanc à la fin du fichier, compté depuis sa fin ; NULL sans blanc détecté.';
COMMENT ON COLUMN sonores.debut_detecte IS 'Blanc au début du fichier, mesuré par l''audit complet ; NULL sans blanc détecté.';

ALTER TABLE banques RENAME COLUMN detection_silences TO detection_blancs;
ALTER TABLE sonores RENAME COLUMN detection_silences TO detection_blancs;
