-- Prêter son nom à l'événement en dessous (https://github.com/dascritch/machincast/issues/399). Référence :
-- doc/fr/spec.md § 3.1 (events, airplay) et § 4.3 (liste de lecture).
--
-- Une émission ou un spécial qui a une fin peut, à la fin de sa liste, ou dès son début si sa liste est vide, laisser
-- jouer l'événement en dessous, le plus souvent le fil musical, sous son propre nom jusqu'à sa fin (lend_name) : son nom
-- public et son masquage valent pour la sortie publique. Le passage reste celui de l'événement en dessous, qui reprend
-- sa liste où il l'a laissée ; airplay.lender_event_id note l'événement qui lui prête son nom.
-- depends: 0004.feed-buffer

ALTER TYPE end_of_list ADD VALUE 'lend_name';

ALTER TABLE airplay ADD COLUMN lender_event_id bigint REFERENCES events (id) ON DELETE SET NULL;

CREATE INDEX airplay_lender ON airplay (lender_event_id);
