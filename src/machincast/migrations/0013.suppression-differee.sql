-- Suppression différée (https://github.com/dascritch/machincast/issues/267) : un sonore, une banque, une séquence ou
-- un événement supprimé depuis l'interface reste en base, daté de la demande (supprime_le), jusqu'à sa péremption ; il
-- se restaure depuis sa fiche. Il ne garde ni son nom ni son emplacement : l'unicité ne vaut plus que pour les
-- éléments qui ne sont pas supprimés. Un sonore dont le fichier a disparu (état supprime) est daté de sa disparition
-- (disparu_le) ; ceux qui l'étaient déjà le sont de leur dernière modification.
-- depends: 0012.feeds

ALTER TABLE sonores ADD COLUMN supprime_le timestamptz, ADD COLUMN disparu_le timestamptz;
ALTER TABLE banques ADD COLUMN supprime_le timestamptz;
ALTER TABLE sequences ADD COLUMN supprime_le timestamptz;
ALTER TABLE evenements ADD COLUMN supprime_le timestamptz;

ALTER TABLE sonores DROP CONSTRAINT sonores_emplacement_key;
CREATE UNIQUE INDEX sonores_emplacement_key ON sonores (emplacement) WHERE supprime_le IS NULL;
ALTER TABLE banques DROP CONSTRAINT banques_nom_interne_key;
CREATE UNIQUE INDEX banques_nom_interne_key ON banques (nom_interne) WHERE supprime_le IS NULL;
ALTER TABLE sequences DROP CONSTRAINT sequences_nom_interne_key;
CREATE UNIQUE INDEX sequences_nom_interne_key ON sequences (nom_interne) WHERE supprime_le IS NULL;
ALTER TABLE evenements DROP CONSTRAINT evenements_nom_interne_key;
CREATE UNIQUE INDEX evenements_nom_interne_key ON evenements (nom_interne) WHERE supprime_le IS NULL;

UPDATE sonores SET disparu_le = modifie_le WHERE etat = 'supprime';

COMMENT ON COLUMN sonores.supprime_le IS 'Demande de suppression depuis l''interface ; NULL : pas supprimé.';
COMMENT ON COLUMN sonores.disparu_le IS 'Disparition du fichier, constatée par l''indexation (état supprime).';
COMMENT ON COLUMN banques.supprime_le IS 'Demande de suppression depuis l''interface ; NULL : pas supprimée.';
COMMENT ON COLUMN sequences.supprime_le IS 'Demande de suppression depuis l''interface ; NULL : pas supprimée.';
COMMENT ON COLUMN evenements.supprime_le IS 'Demande de suppression depuis l''interface ; NULL : pas supprimé.';
