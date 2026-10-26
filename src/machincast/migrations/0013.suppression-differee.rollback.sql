-- Retour à la suppression immédiate : les éléments supprimés, que l'ancien schéma n'aurait plus, sont effacés.

DELETE FROM evenements WHERE supprime_le IS NOT NULL;
DELETE FROM sequences WHERE supprime_le IS NOT NULL;
DELETE FROM banques WHERE supprime_le IS NOT NULL;
DELETE FROM sonores WHERE supprime_le IS NOT NULL;

DROP INDEX evenements_nom_interne_key;
ALTER TABLE evenements ADD CONSTRAINT evenements_nom_interne_key UNIQUE (nom_interne);
DROP INDEX sequences_nom_interne_key;
ALTER TABLE sequences ADD CONSTRAINT sequences_nom_interne_key UNIQUE (nom_interne);
DROP INDEX banques_nom_interne_key;
ALTER TABLE banques ADD CONSTRAINT banques_nom_interne_key UNIQUE (nom_interne);
DROP INDEX sonores_emplacement_key;
ALTER TABLE sonores ADD CONSTRAINT sonores_emplacement_key UNIQUE (emplacement);

ALTER TABLE evenements DROP COLUMN supprime_le;
ALTER TABLE sequences DROP COLUMN supprime_le;
ALTER TABLE banques DROP COLUMN supprime_le;
ALTER TABLE sonores DROP COLUMN disparu_le, DROP COLUMN supprime_le;
