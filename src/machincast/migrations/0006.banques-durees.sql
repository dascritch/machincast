-- Durées minimale et maximale, facultatives, des sonores d'une banque (https://github.com/dascritch/machincast/issues/147).
-- Un sonore qui en sort n'est que signalé par l'interface : rien n'est refusé, la diffusion n'en tient pas compte.
-- depends: 0005.banques-crossfades

ALTER TABLE banques
	ADD COLUMN duree_min interval CHECK (duree_min > '0 s'),
	ADD COLUMN duree_max interval CHECK (duree_max > '0 s'),
	ADD CONSTRAINT banques_durees CHECK (duree_min <= duree_max);

COMMENT ON COLUMN banques.duree_min IS 'Durée en deçà de laquelle un sonore de la banque est signalé ; NULL sans minimum.';
COMMENT ON COLUMN banques.duree_max IS 'Durée au-delà de laquelle un sonore de la banque est signalé ; NULL sans maximum.';
