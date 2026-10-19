-- Deux événements n'ont pas le même nom interne, comme les banques et les séquences : c'est leur nom dans les listes,
-- le log et l'airplay (https://github.com/dascritch/machincast/issues/32).
-- depends: 0001.schema-initial

ALTER TABLE evenements ADD CONSTRAINT evenements_nom_interne_key UNIQUE (nom_interne);
