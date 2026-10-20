-- Annulation de la date de vérification complète (https://github.com/dascritch/machincast/issues/125).

ALTER TABLE sonores DROP COLUMN verifie_le;
