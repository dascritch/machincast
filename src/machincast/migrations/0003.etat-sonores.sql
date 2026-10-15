-- État d'un sonore, à la place du booléen actif (https://github.com/dascritch/machincast/issues/66).
-- Référence : doc/spec.md § 3.1.
--
--   actif      jouable ;
--   desactive  retiré par l'interface : choix humain ;
--   expire     retiré par le binaire lecture : maximum de lectures atteint ou fin de la période de diffusion ;
--   errone     fichier illisible ou endommagé, posé par l'indexeur, qui le rétablit si le fichier redevient sain ;
--   supprime   fichier introuvable, posé par l'indexeur.
--
-- Les valeurs sont sans accents, comme celles des autres types énumérés ; l'interface les affiche accentuées.

CREATE TYPE etat_sonore AS ENUM ('actif', 'desactive', 'expire', 'errone', 'supprime');

-- La conversion ne compte pas comme une modification des sonores : modifie_le reste inchangé.
ALTER TABLE sonores DISABLE TRIGGER sonores_modifie_le;
ALTER TABLE sonores ADD COLUMN etat etat_sonore NOT NULL DEFAULT 'actif';
UPDATE sonores SET etat = 'desactive' WHERE NOT actif;
UPDATE sonores SET champs_edites = array_replace(champs_edites, 'actif', 'etat') WHERE 'actif' = ANY (champs_edites);
ALTER TABLE sonores ENABLE TRIGGER sonores_modifie_le;

-- Supprimer la colonne retire aussi le droit du binaire lecture sur elle.
ALTER TABLE sonores DROP COLUMN actif;

-- Machin_lecture ne modifie que l'état des sonores, pour les passer à expire.
GRANT UPDATE (etat) ON sonores TO machincast_lecture;
