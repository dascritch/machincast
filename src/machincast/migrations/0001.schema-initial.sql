-- Schéma initial de MachinCast. Référence : doc/spec.md § 3.1 (tables) et § 3.2 (rôles et droits).
--
-- Fusion, avant toute mise en production, des quatre premières migrations
-- (https://github.com/dascritch/machincast/pull/70) : schéma (https://github.com/dascritch/machincast/issues/3),
-- rôles et droits (https://github.com/dascritch/machincast/issues/4), état d'un sonore
-- (https://github.com/dascritch/machincast/issues/66) et état aperçu (https://github.com/dascritch/machincast/issues/69).
-- Puis, toujours avant la mise en production, des trois suivantes (https://github.com/dascritch/machincast/pull/90) :
-- élément d'événement des passages (https://github.com/dascritch/machincast/issues/14), priorité « secours » et
-- événement de secours d'un stream (https://github.com/dascritch/machincast/issues/16).
--
-- Textes saisis à la main (noms, artiste, titre, nature) : varchar(255), même limite que l'interface.
-- Chemins, URL et messages détaillés : text, leur longueur n'est pas bornée à l'avance.

-- ─── Types énumérés ────────────────────────────────────────
-- L'ordre de déclaration compte : il permet de comparer et de trier les valeurs.

CREATE TYPE type_sonore AS ENUM ('fichier', 'stream');
CREATE TYPE mode_banque AS ENUM ('sequentiel', 'aleatoire');
-- Ordre croissant de priorité : fil_musical < emission < special. La priorité secours, rangée en dessous, est hors
-- grille : un événement de secours ne joue qu'à la place d'un stream tombé (doc/spec.md § 4.7).
CREATE TYPE priorite_evenement AS ENUM ('secours', 'fil_musical', 'emission', 'special');
CREATE TYPE jour_semaine AS ENUM ('lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche');
CREATE TYPE type_ligne_airplay AS ENUM ('debut', 'fin');
CREATE TYPE niveau_log AS ENUM ('info', 'alerte', 'incident');
-- État d'un sonore, dans l'ordre de sa vie (doc/spec.md § 3.1) :
--   apercu     nouveau fichier, enregistré sans être décodé ; pas jouable ;
--   actif      jouable ;
--   desactive  retiré par l'interface : choix humain ;
--   expire     retiré par le binaire lecture : maximum de lectures atteint ou fin de la période de diffusion ;
--   errone     fichier illisible ou endommagé, posé par l'indexeur, qui le rétablit si le fichier redevient sain ;
--   supprime   fichier introuvable, posé par l'indexeur.
-- Les valeurs sont sans accents, comme celles des autres types énumérés ; l'interface les affiche accentuées.
CREATE TYPE etat_sonore AS ENUM ('apercu', 'actif', 'desactive', 'expire', 'errone', 'supprime');

-- Mise à jour automatique de la colonne modifie_le.
CREATE FUNCTION machincast_maj_modifie_le() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
	NEW.modifie_le := clock_timestamp();
	RETURN NEW;
END;
$$;

-- ─── Marques-pages de streams ──────────────────────────────

CREATE TABLE marques_pages_streams (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	nom varchar(255) NOT NULL UNIQUE,
	url text NOT NULL
);

-- ─── Sonores ───────────────────────────────────────────────

CREATE TABLE sonores (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	type type_sonore NOT NULL,
	emplacement text UNIQUE,
	url_stream text,
	marque_page_id bigint REFERENCES marques_pages_streams (id) ON DELETE RESTRICT,
	-- Stream seulement : événement de secours joué quand le flux tombe ; vide, l'événement de priorité inférieure.
	-- Sa clé étrangère est posée après la table evenements.
	secours_evenement_id bigint,
	-- Artiste et titre servent au masquage, à la recherche et à l'airplay : ce sont des colonnes.
	artiste varchar(255),
	titre varchar(255),
	-- Métadonnées non critiques (année, label, genre…), libres et extensibles sans migration.
	metadonnees_musicales jsonb NOT NULL DEFAULT '{}'
		CHECK (jsonb_typeof(metadonnees_musicales) = 'object'),
	crossfade_debut interval NOT NULL DEFAULT '0 s' CHECK (crossfade_debut >= '0 s'),
	crossfade_fin interval NOT NULL DEFAULT '0 s' CHECK (crossfade_fin >= '0 s'),
	max_lectures integer CHECK (max_lectures > 0),
	etat etat_sonore NOT NULL DEFAULT 'actif',
	masquer_metadonnees boolean,
	duree interval CHECK (duree > '0 s'),
	debut_diffusion timestamptz,
	fin_diffusion timestamptz,
	fichier_modifie_le timestamptz,
	fichier_taille bigint CHECK (fichier_taille >= 0),
	champs_edites text[] NOT NULL DEFAULT '{}',
	indexe_le timestamptz,
	modifie_le timestamptz NOT NULL DEFAULT clock_timestamp(),
	CONSTRAINT sonores_fichier_ou_stream CHECK (
		(type = 'fichier' AND emplacement IS NOT NULL AND url_stream IS NULL AND marque_page_id IS NULL)
		OR (type = 'stream' AND emplacement IS NULL AND num_nonnulls(url_stream, marque_page_id) = 1)
	),
	CONSTRAINT sonores_duree_fichier CHECK (type = 'fichier' OR duree IS NULL),
	CONSTRAINT sonores_periode CHECK (fin_diffusion > debut_diffusion)
);

CREATE TRIGGER sonores_modifie_le BEFORE UPDATE ON sonores
	FOR EACH ROW EXECUTE FUNCTION machincast_maj_modifie_le();

-- ─── Banques ───────────────────────────────────────────────

CREATE TABLE banques (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	nom_interne varchar(255) NOT NULL UNIQUE,
	mode mode_banque NOT NULL,
	masquer_metadonnees boolean,
	modifie_le timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TRIGGER banques_modifie_le BEFORE UPDATE ON banques
	FOR EACH ROW EXECUTE FUNCTION machincast_maj_modifie_le();

-- Répertoires indexés d'une banque : une banque peut en avoir plusieurs,
-- et un même répertoire peut alimenter plusieurs banques.
CREATE TABLE banques_repertoires (
	banque_id bigint NOT NULL REFERENCES banques (id) ON DELETE CASCADE,
	repertoire text NOT NULL,
	PRIMARY KEY (banque_id, repertoire)
);

CREATE INDEX banques_repertoires_repertoire ON banques_repertoires (repertoire);

-- Un sonore figure au plus une fois dans une banque ; il peut appartenir à plusieurs banques.
-- L'unicité des positions est différée à la fin de la transaction, pour permettre de réordonner.
CREATE TABLE banques_sonores (
	banque_id bigint NOT NULL REFERENCES banques (id) ON DELETE CASCADE,
	sonore_id bigint NOT NULL REFERENCES sonores (id) ON DELETE CASCADE,
	position integer NOT NULL CHECK (position > 0),
	PRIMARY KEY (banque_id, sonore_id),
	CONSTRAINT banques_sonores_position UNIQUE (banque_id, position) DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX banques_sonores_sonore ON banques_sonores (sonore_id);

-- ─── Événements ────────────────────────────────────────────

CREATE TABLE evenements (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	nom_interne varchar(255) NOT NULL,
	nom_public varchar(255),
	priorite priorite_evenement NOT NULL,
	debut timestamptz,
	fin timestamptz,
	-- Jours de la semaine où l'événement se répète. Vide = pas de récurrence.
	jours_recurrence jour_semaine[] NOT NULL DEFAULT '{}',
	masquer_metadonnees boolean,
	modifie_le timestamptz NOT NULL DEFAULT clock_timestamp(),
	-- Seuls un fil musical (fil permanent) et un événement de secours peuvent n'avoir aucune date de début.
	CONSTRAINT evenements_debut CHECK (debut IS NOT NULL OR priorite IN ('fil_musical', 'secours')),
	-- Un événement de secours est hors grille : ni début, ni fin, ni jours de récurrence.
	CONSTRAINT evenements_secours_hors_grille
		CHECK (priorite <> 'secours' OR (debut IS NULL AND fin IS NULL AND jours_recurrence = '{}')),
	-- Pas de fin sans début.
	CONSTRAINT evenements_fin_sans_debut CHECK (fin IS NULL OR debut IS NOT NULL),
	CONSTRAINT evenements_ordre CHECK (fin > debut)
);

CREATE TRIGGER evenements_modifie_le BEFORE UPDATE ON evenements
	FOR EACH ROW EXECUTE FUNCTION machincast_maj_modifie_le();

-- Événement de secours d'un stream. Un événement supprimé laisse le stream sans secours.
ALTER TABLE sonores
	ADD CONSTRAINT sonores_secours_evenement
		FOREIGN KEY (secours_evenement_id) REFERENCES evenements (id) ON DELETE SET NULL,
	ADD CONSTRAINT sonores_secours_stream CHECK (type = 'stream' OR secours_evenement_id IS NULL);

CREATE INDEX sonores_secours_evenement ON sonores (secours_evenement_id);

-- Le secours d'un stream est toujours un événement de priorité secours : vérifié à l'enregistrement du sonore,
-- et quand la priorité d'un événement désigné change. Conditions imbriquées : la requête sur l'autre table n'est
-- préparée que lorsqu'elle est nécessaire ; l'indexeur, qui enregistre des fichiers sans droit de lire les
-- événements, ne la déclenche jamais.
CREATE FUNCTION machincast_verifier_secours_sonore() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
	IF NEW.secours_evenement_id IS NOT NULL THEN
		IF NOT EXISTS (SELECT 1 FROM evenements WHERE id = NEW.secours_evenement_id AND priorite = 'secours') THEN
			RAISE EXCEPTION 'l''événement % n''est pas un événement de secours', NEW.secours_evenement_id
				USING ERRCODE = 'check_violation';
		END IF;
	END IF;
	RETURN NEW;
END;
$$;

CREATE TRIGGER sonores_secours BEFORE INSERT OR UPDATE OF secours_evenement_id ON sonores
	FOR EACH ROW EXECUTE FUNCTION machincast_verifier_secours_sonore();

CREATE FUNCTION machincast_verifier_secours_evenement() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
	IF OLD.priorite = 'secours' AND NEW.priorite <> 'secours' THEN
		IF EXISTS (SELECT 1 FROM sonores WHERE secours_evenement_id = NEW.id) THEN
			RAISE EXCEPTION 'l''événement % sert de secours à un stream : il reste de priorité secours', NEW.id
				USING ERRCODE = 'check_violation';
		END IF;
	END IF;
	RETURN NEW;
END;
$$;

CREATE TRIGGER evenements_secours BEFORE UPDATE OF priorite ON evenements
	FOR EACH ROW EXECUTE FUNCTION machincast_verifier_secours_evenement();

-- Liste de lecture ordonnée d'un événement : chaque élément est une banque ou un sonore.
-- Un même élément peut revenir plusieurs fois.
CREATE TABLE evenements_elements (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	evenement_id bigint NOT NULL REFERENCES evenements (id) ON DELETE CASCADE,
	position integer NOT NULL CHECK (position > 0),
	banque_id bigint REFERENCES banques (id) ON DELETE CASCADE,
	sonore_id bigint REFERENCES sonores (id) ON DELETE CASCADE,
	CONSTRAINT evenements_elements_banque_ou_sonore CHECK (num_nonnulls(banque_id, sonore_id) = 1),
	CONSTRAINT evenements_elements_position UNIQUE (evenement_id, position) DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX evenements_elements_banque ON evenements_elements (banque_id);
CREATE INDEX evenements_elements_sonore ON evenements_elements (sonore_id);

-- ─── Airplay ───────────────────────────────────────────────

-- Historique de diffusion : une ligne au début et une ligne à la fin de chaque passage.
-- Les lignes ne sont jamais supprimées ; les références passent à NULL quand l'élément est supprimé,
-- et l'emplacement (chemin ou URL), l'artiste et le titre sont recopiés au moment du passage.
CREATE TABLE airplay (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	passage_id uuid NOT NULL,
	type_ligne type_ligne_airplay NOT NULL,
	horodatage timestamptz NOT NULL DEFAULT clock_timestamp(),
	sonore_id bigint REFERENCES sonores (id) ON DELETE SET NULL,
	banque_id bigint REFERENCES banques (id) ON DELETE SET NULL,
	evenement_id bigint REFERENCES evenements (id) ON DELETE SET NULL,
	-- Élément de la liste qui a fait jouer le passage : un même élément peut figurer plusieurs fois dans une liste,
	-- seul lui dit où la reprendre, à l'élément qui suit le dernier joué.
	element_id bigint REFERENCES evenements_elements (id) ON DELETE SET NULL,
	emplacement text,
	artiste varchar(255),
	titre varchar(255),
	duree_diffusee interval CHECK (duree_diffusee >= '0 s'),
	sans_incident boolean,
	CONSTRAINT airplay_un_debut_une_fin UNIQUE (passage_id, type_ligne),
	CONSTRAINT airplay_champs_de_fin CHECK (
		(type_ligne = 'debut' AND duree_diffusee IS NULL AND sans_incident IS NULL)
		OR (type_ligne = 'fin' AND duree_diffusee IS NOT NULL AND sans_incident IS NOT NULL)
	)
);

CREATE INDEX airplay_horodatage ON airplay (horodatage);
CREATE INDEX airplay_banque ON airplay (banque_id, horodatage);
CREATE INDEX airplay_sonore ON airplay (sonore_id, horodatage);
CREATE INDEX airplay_evenement ON airplay (evenement_id, horodatage);

-- ─── Log ───────────────────────────────────────────────────

CREATE TABLE log (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	horodatage timestamptz NOT NULL DEFAULT clock_timestamp(),
	niveau niveau_log NOT NULL,
	nature varchar(255) NOT NULL,
	message text NOT NULL DEFAULT '',
	sonore_id bigint REFERENCES sonores (id) ON DELETE SET NULL,
	banque_id bigint REFERENCES banques (id) ON DELETE SET NULL,
	evenement_id bigint REFERENCES evenements (id) ON DELETE SET NULL
);

CREATE INDEX log_horodatage ON log (horodatage);
CREATE INDEX log_incidents ON log (horodatage) WHERE niveau <> 'info';

-- ─── Rôles et droits ───────────────────────────────────────
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
-- Lit la programmation, passe les sonores à l'état expire (colonne etat seule), écrit l'airplay et le log.
-- Pas de lecture du log : une insertion dans log ne doit pas utiliser RETURNING.

GRANT SELECT ON sonores, marques_pages_streams, banques, banques_sonores, evenements, evenements_elements
	TO machincast_lecture;
GRANT UPDATE (etat) ON sonores TO machincast_lecture;
GRANT SELECT, INSERT ON airplay TO machincast_lecture;
GRANT INSERT ON log TO machincast_lecture;

-- ─── Machin_indexation ─────────────────────────────────────
-- Lit les banques et leurs répertoires, crée et met à jour les sonores, les rattache à leur banque.
-- Ne supprime rien : un fichier disparu fait passer son sonore à l'état supprime.

GRANT SELECT, INSERT, UPDATE ON sonores TO machincast_indexation;
GRANT SELECT ON banques, banques_repertoires TO machincast_indexation;
GRANT SELECT, INSERT ON banques_sonores TO machincast_indexation;

-- ─── Machin_interface ──────────────────────────────────────
-- Gère toute la programmation ; consulte l'airplay et le log sans pouvoir les modifier.

GRANT SELECT, INSERT, UPDATE, DELETE
	ON sonores, marques_pages_streams, banques, banques_repertoires, banques_sonores, evenements, evenements_elements
	TO machincast_interface;
GRANT SELECT ON airplay, log TO machincast_interface;
