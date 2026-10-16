-- Annulation de la marque « ne pas répéter » des banques (https://github.com/dascritch/machincast/issues/63).

ALTER TABLE banques DROP COLUMN ne_pas_repeter;
