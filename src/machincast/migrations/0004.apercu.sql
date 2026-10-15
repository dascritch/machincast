-- État « aperçu » d'un sonore (https://github.com/dascritch/machincast/issues/69).
-- Un nouveau fichier est enregistré à l'état apercu, sans être décodé : l'indexation rapide ne décode que ces
-- sonores, l'audit complet les décode tous. Un sonore en aperçu n'est pas jouable.
-- La valeur se place avant actif, dans l'ordre de la vie d'un sonore.

ALTER TYPE etat_sonore ADD VALUE 'apercu' BEFORE 'actif';
