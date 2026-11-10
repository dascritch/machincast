-- La priorité « imprévu » (breaking), au-dessus de « spécial » (https://github.com/dascritch/machincast/issues/402).
-- Référence : doc/fr/spec.md § 3.1 (events) et § 4.1 (événement actif).
--
-- Un imprévu signale une situation qu'on ne programme pas, comme une alerte de la sécurité civile : il a un début, une
-- seule occurrence, jamais de récurrence. Il choisit sa fin de liste comme un spécial. Une valeur ajoutée à un type
-- énuméré ne peut pas servir dans la transaction qui l'ajoute : les contraintes la comparent en texte.
-- depends: 0006.player-runs

ALTER TYPE event_priority ADD VALUE 'breaking' AFTER 'special';

ALTER TABLE events
	ADD CONSTRAINT events_breaking_once CHECK (priority::text <> 'breaking' OR recurrence_days = '{}'),
	DROP CONSTRAINT events_end_of_list,
	ADD CONSTRAINT events_end_of_list
		CHECK (end_of_list = 'replay' OR (ends_at IS NOT NULL AND priority::text IN ('show', 'special', 'breaking')));
