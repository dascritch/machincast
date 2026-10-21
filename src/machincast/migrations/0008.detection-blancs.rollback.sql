-- Annulation de la détection de blanc (https://github.com/dascritch/machincast/issues/146).

ALTER TABLE banques
	DROP COLUMN detection_blancs;

ALTER TABLE sonores
	DROP COLUMN detection_blancs,
	DROP COLUMN fin_detectee,
	DROP COLUMN debut_detecte;
