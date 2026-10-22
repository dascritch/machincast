-- Annulation de la position des fondus d'une banque (https://github.com/dascritch/machincast/issues/234).

ALTER TABLE banques
	DROP COLUMN position_fondu_sortie,
	DROP COLUMN position_fondu_entree;

DROP TYPE position_fondu;
