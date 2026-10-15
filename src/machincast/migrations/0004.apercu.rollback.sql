-- Annulation de l'état « aperçu » (https://github.com/dascritch/machincast/issues/69).
-- PostgreSQL ne sait pas retirer une valeur d'un type énuméré : le type est recréé sans elle. Un sonore en aperçu
-- redevient actif : sans indexation rapide, l'indexeur décode tous les sonores à chaque passage.
-- Le droit du binaire lecture sur la colonne etat est conservé par le changement de type.

ALTER TABLE sonores ALTER COLUMN etat DROP DEFAULT;
CREATE TYPE etat_sonore_sans_apercu AS ENUM ('actif', 'desactive', 'expire', 'errone', 'supprime');
ALTER TABLE sonores ALTER COLUMN etat TYPE etat_sonore_sans_apercu
	USING (CASE WHEN etat = 'apercu' THEN 'actif' ELSE etat::text END)::etat_sonore_sans_apercu;
DROP TYPE etat_sonore;
ALTER TYPE etat_sonore_sans_apercu RENAME TO etat_sonore;
ALTER TABLE sonores ALTER COLUMN etat SET DEFAULT 'actif';
