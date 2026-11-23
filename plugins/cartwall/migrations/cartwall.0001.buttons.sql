-- Les boutons du cartouchier, par compte de l'API (https://github.com/dascritch/machincast/issues/512) : leur
-- intitulé, leur couleur, et l'action d'antenne qu'ils demandent à Machin player, avec ce qu'elle vise.

CREATE TABLE cartwall_buttons (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	api_user_id bigint NOT NULL REFERENCES api_users (id) ON DELETE CASCADE,
	position integer NOT NULL CHECK (position >= 1),
	label varchar(64) NOT NULL CHECK (btrim(label) <> ''),
	colour char(7) NOT NULL DEFAULT '#3a6ea5' CHECK (colour ~ '^#[0-9a-f]{6}$'),
	action text NOT NULL CHECK (action IN (
		'skip_sound', 'skip_sequence', 'cut_to_background', 'restart_sound', 'restart_event', 'restart_sequence',
		'advance', 'cut_by_fallback', 'cut_by_feed', 'insert_sequence', 'insert_bank'
	)),
	sequence_id bigint REFERENCES sequences (id) ON DELETE CASCADE,
	bank_id bigint REFERENCES banks (id) ON DELETE CASCADE,
	event_id bigint REFERENCES events (id) ON DELETE CASCADE,
	feed_id bigint REFERENCES feeds (id) ON DELETE CASCADE,
	-- Le blanc de 5 secondes d'une insertion (https://github.com/dascritch/machincast/issues/594).
	blank text CHECK (blank IN ('before', 'after', 'both')),
	CONSTRAINT cartwall_buttons_position UNIQUE (api_user_id, position) DEFERRABLE INITIALLY IMMEDIATE,
	-- Chaque action vise ce qu'il lui faut, et rien d'autre.
	CONSTRAINT cartwall_buttons_target CHECK (
		(sequence_id IS NOT NULL) = (action = 'insert_sequence')
		AND (bank_id IS NOT NULL) = (action = 'insert_bank')
		AND (event_id IS NOT NULL) = (action = 'cut_by_fallback')
		AND (feed_id IS NOT NULL) = (action = 'cut_by_feed')
		AND ((blank IS NULL) OR (action IN ('insert_sequence', 'insert_bank')))
	)
);

COMMENT ON TABLE cartwall_buttons IS 'Les boutons du cartouchier de chaque compte de l''API, dans l''ordre de position.';

GRANT SELECT ON cartwall_buttons TO machincast_intranet;
GRANT SELECT, INSERT, UPDATE, DELETE ON cartwall_buttons TO machincast_interface;
