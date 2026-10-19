-- Annulation de l'unicité du nom interne d'un événement (https://github.com/dascritch/machincast/issues/32).

ALTER TABLE evenements DROP CONSTRAINT evenements_nom_interne_key;
