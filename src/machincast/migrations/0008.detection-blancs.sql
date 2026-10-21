-- Détection de blanc (https://github.com/dascritch/machincast/issues/146). L'audit complet mesure, au seuil de la
-- configuration (blancs.seuil), le blanc au début et à la fin du fichier d'un sonore. La fin détectée se compte depuis
-- la fin du fichier : c'est la durée du blanc final. Le fichier sonore n'est jamais touché, seule la base retient ces
-- durées. La détection ne s'applique pas par défaut : un sonore est joué sans ses blancs s'il l'active, ou si la
-- banque qui l'a fourni l'active.
-- depends: 0007.sonores-crossfades-facultatifs

ALTER TABLE sonores
	ADD COLUMN debut_detecte interval CHECK (debut_detecte >= '0 s'),
	ADD COLUMN fin_detectee interval CHECK (fin_detectee >= '0 s'),
	ADD COLUMN detection_blancs boolean NOT NULL DEFAULT false;

ALTER TABLE banques
	ADD COLUMN detection_blancs boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN sonores.debut_detecte IS 'Blanc au début du fichier, mesuré par l''audit complet ; NULL sans blanc détecté.';
COMMENT ON COLUMN sonores.fin_detectee IS 'Blanc à la fin du fichier, compté depuis sa fin ; NULL sans blanc détecté.';
COMMENT ON COLUMN sonores.detection_blancs IS 'Le sonore est joué sans ses blancs détectés, même hors d''une banque qui les retire.';
COMMENT ON COLUMN banques.detection_blancs IS 'Les sonores joués via la banque le sont sans leurs blancs détectés.';
