-- Annulation de l'état d'un sonore (https://github.com/dascritch/machincast/issues/66) :
-- seul l'état actif redevient actif = true ; tous les autres états deviennent actif = false.

ALTER TABLE sonores DISABLE TRIGGER sonores_modifie_le;
ALTER TABLE sonores ADD COLUMN actif boolean NOT NULL DEFAULT true;
UPDATE sonores SET actif = (etat = 'actif');
UPDATE sonores SET champs_edites = array_replace(champs_edites, 'etat', 'actif') WHERE 'etat' = ANY (champs_edites);
ALTER TABLE sonores ENABLE TRIGGER sonores_modifie_le;

ALTER TABLE sonores DROP COLUMN etat;
DROP TYPE etat_sonore;

GRANT UPDATE (actif) ON sonores TO machincast_lecture;
