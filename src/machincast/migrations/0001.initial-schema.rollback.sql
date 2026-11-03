-- Annulation du schéma initial (https://github.com/dascritch/machincast/pull/70, fusions :
-- https://github.com/dascritch/machincast/pull/90, https://github.com/dascritch/machincast/pull/100 et
-- https://github.com/dascritch/machincast/issues/314 ; noms anglais :
-- https://github.com/dascritch/machincast/issues/358).
-- Les rôles ne sont pas supprimés : ils appartiennent au serveur et servent aussi à l'autre base.

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM machincast_player, machincast_indexer, machincast_interface;
REVOKE USAGE ON SCHEMA public FROM machincast_player, machincast_indexer, machincast_interface;

DROP TABLE log;
DROP TABLE airplay;
DROP TABLE event_skips;
DROP TABLE event_items;
DROP TABLE sequence_items;
DROP TABLE sequences;
ALTER TABLE sounds DROP CONSTRAINT sounds_fallback_event;
DROP TABLE events;
DROP TABLE bank_sounds;
DROP TABLE bank_directories;
DROP TABLE banks;
DROP TABLE sounds;
DROP TABLE feeds;
DROP FUNCTION machincast_check_event_fallback();
DROP FUNCTION machincast_check_sound_fallback();
DROP FUNCTION machincast_set_modified_at();
DROP TYPE crossfade_rule;
DROP TYPE sound_state;
DROP TYPE log_level;
DROP TYPE airplay_line_type;
DROP TYPE weekday;
DROP TYPE event_priority;
DROP TYPE bank_mode;
DROP TYPE sound_type;
