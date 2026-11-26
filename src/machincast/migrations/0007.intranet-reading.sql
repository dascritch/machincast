-- L'API de l'intranet lit la programmation, l'airplay et le log (https://github.com/dascritch/machincast/issues/540),
-- sans rien en écrire.

GRANT SELECT ON sounds, feeds, banks, bank_directories, bank_sounds, events, event_items, event_skips, sequences,
	sequence_items, airplay, log TO machincast_webserver;
