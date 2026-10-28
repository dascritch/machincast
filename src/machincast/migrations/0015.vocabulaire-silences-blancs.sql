-- Vocabulaire (https://github.com/dascritch/machincast/issues/291) : le son faible au début ou à la fin d'un fichier,
-- que l'audit complet mesure et où se placent les fondus, est un silence ; l'absence de tout son à l'antenne est un
-- blanc. Les colonnes de la détection de silence sont renommées, et les alertes déjà consignées pour rien à diffuser
-- prennent la nature « blanc », celle qu'écrit désormais Machin lecture. Les droits suivent les colonnes renommées.
-- depends: 0014.sessions-sautees

ALTER TABLE sonores RENAME COLUMN detection_blancs TO detection_silences;
ALTER TABLE banques RENAME COLUMN detection_blancs TO detection_silences;

COMMENT ON COLUMN sonores.debut_detecte IS 'Silence au début du fichier, mesuré par l''audit complet ; NULL sans silence détecté.';
COMMENT ON COLUMN sonores.fin_detectee IS 'Silence à la fin du fichier, compté depuis sa fin ; NULL sans silence détecté.';
COMMENT ON COLUMN sonores.detection_silences IS 'Le sonore est joué sans ses silences détectés, même hors d''une banque qui les retire.';
COMMENT ON COLUMN banques.detection_silences IS 'Les sonores joués via la banque le sont sans leurs silences détectés.';
COMMENT ON COLUMN sonores.audite_le IS 'Date du dernier audit complet du fichier, silences mesurés ; NULL jamais audité.';
COMMENT ON COLUMN sonores.audit_seuil IS 'Seuil de silence, en dB crête, du dernier audit complet ; NULL jamais audité.';

UPDATE log SET nature = 'blanc' WHERE nature = 'silence';
