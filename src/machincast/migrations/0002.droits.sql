-- Rôles et droits par binaire (https://github.com/dascritch/machincast/issues/4).
-- Référence : doc/spec.md § 3.2.
--
-- Les trois rôles sont des rôles de groupe, sans connexion. Un utilisateur système se connecte
-- avec son propre rôle (authentification peer), membre de ces groupes SANS en hériter les droits :
-- chaque binaire endosse explicitement son rôle par SET ROLE à la connexion (machincast.base.connecter).
--
-- Les rôles appartiennent au serveur PostgreSQL, pas à une base : ils sont partagés par la base de
-- production et la base de test. Ils sont donc créés seulement s'ils n'existent pas encore.

DO $$
DECLARE
	role text;
BEGIN
	FOREACH role IN ARRAY ARRAY['machincast_lecture', 'machincast_indexation', 'machincast_interface'] LOOP
		IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = role) THEN
			EXECUTE format('CREATE ROLE %I NOLOGIN', role);
		END IF;
	END LOOP;
END;
$$;

GRANT USAGE ON SCHEMA public TO machincast_lecture, machincast_indexation, machincast_interface;

-- ─── Machin_lecture ────────────────────────────────────────
-- Lit la programmation, désactive les sonores (colonne actif seule), écrit l'airplay et le log.
-- Pas de lecture du log : une insertion dans log ne doit pas utiliser RETURNING.

GRANT SELECT ON sonores, marques_pages_streams, banques, banques_sonores, evenements, evenements_elements
	TO machincast_lecture;
GRANT UPDATE (actif) ON sonores TO machincast_lecture;
GRANT SELECT, INSERT ON airplay TO machincast_lecture;
GRANT INSERT ON log TO machincast_lecture;

-- ─── Machin_indexation ─────────────────────────────────────
-- Lit les banques et leurs répertoires, crée et met à jour les sonores, les rattache à leur banque.
-- Ne supprime rien : un fichier disparu rend son sonore inactif.

GRANT SELECT, INSERT, UPDATE ON sonores TO machincast_indexation;
GRANT SELECT ON banques, banques_repertoires TO machincast_indexation;
GRANT SELECT, INSERT ON banques_sonores TO machincast_indexation;

-- ─── Machin_interface ──────────────────────────────────────
-- Gère toute la programmation ; consulte l'airplay et le log sans pouvoir les modifier.

GRANT SELECT, INSERT, UPDATE, DELETE
	ON sonores, marques_pages_streams, banques, banques_repertoires, banques_sonores, evenements, evenements_elements
	TO machincast_interface;
GRANT SELECT ON airplay, log TO machincast_interface;
