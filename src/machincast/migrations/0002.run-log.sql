-- Démarrages et fins de Machin indexer, Machin maintenance-db et Machin purge dans le log
-- (https://github.com/dascritch/machincast/issues/341). Référence : doc/fr/spec.md § 3.2 (rôles et droits) et § 5.2
-- (log).
--
-- Chaque lancement note son démarrage, ligne « start » « <binaire> <version>, pid <pid>[: <options>] », et sa fin,
-- ligne « end » « <binaire>, pid <pid>: exit code <code> ». Un démarrage précédent sans fin, dont le processus ne
-- tourne plus, est un plantage probable, que le lancement suivant note en incident : machincast_previous_start le
-- retrouve, sans que le rôle de l'indexation ait à lire le log.
-- depends: 0001.initial-schema

-- Le dernier démarrage noté de ce binaire, son pid, et s'il a noté sa fin depuis ; aucune ligne s'il n'en a noté aucun.
-- SECURITY DEFINER : elle lit le log avec les droits du propriétaire de la base, et ne rend que ces trois valeurs.
CREATE FUNCTION machincast_previous_start(program text)
RETURNS TABLE (started_at timestamptz, pid integer, ended boolean)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public
AS $$
	SELECT s.logged_at, p.pid, EXISTS (
		SELECT FROM log e
		WHERE e.kind = 'end' AND e.logged_at >= s.logged_at
			AND starts_with(e.message, program || ', pid ' || p.pid || ':')
	)
	FROM log s
	CROSS JOIN LATERAL (SELECT substring(s.message FROM ', pid ([0-9]+)')::integer AS pid) p
	WHERE s.kind = 'start' AND starts_with(s.message, program || ' ') AND p.pid IS NOT NULL
	ORDER BY s.logged_at DESC, s.id DESC
	LIMIT 1
$$;

-- Une fonction est exécutable par tous à sa création : seuls l'indexation et le propriétaire de la base s'en servent.
REVOKE ALL ON FUNCTION machincast_previous_start(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION machincast_previous_start(text) TO machincast_indexer;

-- ─── Machin_indexer ─────────────────────────────────────
-- Note ses démarrages, ses fins et les plantages probables de ses lancements précédents ; ne lit pas le log.
GRANT INSERT ON log TO machincast_indexer;
