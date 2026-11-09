-- Annulation de la mémoire tampon d'un feed (https://github.com/dascritch/machincast/issues/351).

ALTER TABLE feeds DROP CONSTRAINT feeds_buffer_duration, DROP COLUMN buffer_duration;
