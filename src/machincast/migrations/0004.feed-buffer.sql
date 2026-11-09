-- Mémoire tampon d'un feed (https://github.com/dascritch/machincast/issues/351). Référence : doc/fr/spec.md § 3.1
-- (feeds) et § 4.7 (streams).
--
-- Le stream d'un feed attend que sa mémoire tampon soit pleine pour jouer : courte, il démarre vite mais tient mal
-- un réseau irrégulier ; longue, il tient mieux mais met plus de temps à démarrer et à redémarrer. De 2 à 10
-- secondes ; 2 par défaut, le plus proche du stream d'avant, qui jouait dès son premier son.
-- depends: 0003.end-of-list

ALTER TABLE feeds
	ADD COLUMN buffer_duration interval NOT NULL DEFAULT '2 seconds',
	ADD CONSTRAINT feeds_buffer_duration CHECK (buffer_duration BETWEEN '2 seconds' AND '10 seconds');
