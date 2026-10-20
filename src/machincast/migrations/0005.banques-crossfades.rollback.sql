-- Annulation des crossfades d'une banque (https://github.com/dascritch/machincast/issues/143).

ALTER TABLE banques
	DROP COLUMN crossfade_debut_regle,
	DROP COLUMN crossfade_debut,
	DROP COLUMN crossfade_fin_regle,
	DROP COLUMN crossfade_fin;

DROP TYPE regle_crossfade;
