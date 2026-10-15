-- Élément d'événement joué par chaque passage (https://github.com/dascritch/machincast/issues/14).
-- Une même banque ou un même sonore peut figurer plusieurs fois dans la liste d'un événement : seul l'élément
-- dit où reprendre la liste, à l'élément qui suit le dernier joué. Un élément supprimé laisse la ligne d'airplay,
-- sans référence.
-- depends: 0001.schema-initial

ALTER TABLE airplay
	ADD COLUMN element_id bigint REFERENCES evenements_elements (id) ON DELETE SET NULL;
