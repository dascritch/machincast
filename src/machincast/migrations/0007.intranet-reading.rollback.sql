-- Annulation de la lecture par l'API de l'intranet (https://github.com/dascritch/machincast/issues/540).

REVOKE SELECT ON sounds, feeds, banks, bank_directories, bank_sounds, events, event_items, event_skips, sequences,
	sequence_items, airplay, log FROM machincast_webserver;
