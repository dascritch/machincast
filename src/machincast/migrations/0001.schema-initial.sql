-- Schéma initial de MachinCast. Référence : doc/spec.md § 3.1 (tables) et § 3.2 (rôles et droits).
--
-- Fusion, avant toute mise en production, des quatre premières migrations
-- (https://github.com/dascritch/machincast/pull/70) : schéma (https://github.com/dascritch/machincast/issues/3),
-- rôles et droits (https://github.com/dascritch/machincast/issues/4), état d'un sonore
-- (https://github.com/dascritch/machincast/issues/66) et état aperçu (https://github.com/dascritch/machincast/issues/69).
-- Puis, toujours avant la mise en production, des trois suivantes (https://github.com/dascritch/machincast/pull/90) :
-- élément d'événement des passages (https://github.com/dascritch/machincast/issues/14), priorité « secours » et
-- événement de secours d'un stream (https://github.com/dascritch/machincast/issues/16).
-- Puis, encore avant la mise en production, des deux suivantes (https://github.com/dascritch/machincast/pull/100) :
-- banque « ne pas répéter » (https://github.com/dascritch/machincast/issues/63), séquences et nom public des banques
-- (https://github.com/dascritch/machincast/issues/99).
-- Enfin, avant que le projet serve réellement, des quatorze suivantes
-- (https://github.com/dascritch/machincast/issues/314), de 0002.evenements-nom-unique à
-- 0015.vocabulaire-silences-blancs : leurs colonnes sont ajoutées à la fin de leur table, dans l'ordre où elles sont
-- arrivées, pour que ce schéma soit exactement celui d'une base qui les a toutes reçues. Une telle base garde ses
-- données : machincast.base.oublier_les_migrations_fusionnees retire leurs traces de _yoyo_migration.
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
--   non_supporte  fichier qui n'est pas du son, d'après son type lu par libmagic
--                 (https://github.com/dascritch/machincast/issues/121).
CREATE TYPE etat_sonore AS ENUM ('apercu', 'actif', 'desactive', 'expire', 'errone', 'non_supporte', 'supprime');
-- Crossfades d'une banque, pour les sonores qu'elle fait jouer (https://github.com/dascritch/machincast/issues/143) :
-- « sonore » garde le crossfade du sonore, « a_defaut » donne celui de la banque à un sonore qui n'en a pas de
-- paramétré, « impose » donne celui de la banque à tout sonore.
CREATE TYPE regle_crossfade AS ENUM ('sonore', 'a_defaut', 'impose');

-- Mise à jour automatique de la colonne modifie_le.
CREATE FUNCTION machincast_maj_modifie_le() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
	NEW.modifie_le := clock_timestamp();
	RETURN NEW;
END;
$$;

-- ─── Feeds ─────────────────────────────────────────────────
-- Adresses de streams nommées, qu'un sonore stream peut suivre (https://github.com/dascritch/machincast/issues/252).

CREATE TABLE feeds (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	nom varchar(255) NOT NULL UNIQUE,
	url text NOT NULL
);

COMMENT ON TABLE feeds IS 'Feeds : adresses de streams nommées, qu''un sonore stream peut suivre (feed_id).';

-- ─── Sonores ───────────────────────────────────────────────

CREATE TABLE sonores (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	type type_sonore NOT NULL,
	-- Unique parmi les sonores qui ne sont pas supprimés : voir sonores_emplacement_key.
	emplacement text,
	url_stream text,
	feed_id bigint REFERENCES feeds (id) ON DELETE RESTRICT,
	-- Stream seulement : événement de secours joué quand le flux tombe ; vide, l'événement de priorité inférieure.
	-- Sa clé étrangère est posée après la table evenements.
	secours_evenement_id bigint,
	-- Artiste et titre servent au masquage, à la recherche et à l'airplay : ce sont des colonnes.
	artiste varchar(255),
	titre varchar(255),
	-- Métadonnées non critiques (année, label, genre…), libres et extensibles sans migration.
	metadonnees_musicales jsonb NOT NULL DEFAULT '{}'
		CHECK (jsonb_typeof(metadonnees_musicales) = 'object'),
	-- NULL : pas paramétré, celui de la banque ou de la configuration ; 0 seconde en est un
	-- (https://github.com/dascritch/machincast/issues/145).
	crossfade_debut interval CHECK (crossfade_debut >= '0 s'),
	crossfade_fin interval CHECK (crossfade_fin >= '0 s'),
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
	-- Type réel du fichier, lu par libmagic (https://github.com/dascritch/machincast/issues/121).
	type_mime text,
	-- Dernière vérification complète du fichier : son type lu, puis son décodage
	-- (https://github.com/dascritch/machincast/issues/125).
	verifie_le timestamptz,
	-- Silences au début et à la fin du fichier, mesurés par l'audit complet ; la fin détectée se compte depuis la fin
	-- du fichier. Le fichier n'est jamais touché (https://github.com/dascritch/machincast/issues/146).
	debut_detecte interval CHECK (debut_detecte >= '0 s'),
	fin_detectee interval CHECK (fin_detectee >= '0 s'),
	detection_silences boolean NOT NULL DEFAULT false,
	-- La prochaine indexation, même rapide, fait l'audit complet du sonore
	-- (https://github.com/dascritch/machincast/issues/114).
	audit_demande boolean NOT NULL DEFAULT false,
	-- Dernier audit complet, et son seuil de silence (https://github.com/dascritch/machincast/issues/206).
	audite_le timestamptz,
	audit_seuil double precision CHECK (audit_seuil >= -100 AND audit_seuil < 0),
	-- Suppression différée (https://github.com/dascritch/machincast/issues/267) : demandée depuis l'interface, ou
	-- disparition du fichier constatée par l'indexation (état supprime).
	supprime_le timestamptz,
	disparu_le timestamptz,
	CONSTRAINT sonores_fichier_ou_stream CHECK (
		(type = 'fichier' AND emplacement IS NOT NULL AND url_stream IS NULL AND feed_id IS NULL)
		OR (type = 'stream' AND emplacement IS NULL AND num_nonnulls(url_stream, feed_id) = 1)
	),
	CONSTRAINT sonores_duree_fichier CHECK (type = 'fichier' OR duree IS NULL),
	CONSTRAINT sonores_periode CHECK (fin_diffusion > debut_diffusion),
	CONSTRAINT sonores_audit CHECK ((audite_le IS NULL) = (audit_seuil IS NULL))
);

-- Un élément supprimé ne garde ni son nom ni son emplacement : l'unicité ne vaut que pour ceux qui ne le sont pas
-- (https://github.com/dascritch/machincast/issues/267).
CREATE UNIQUE INDEX sonores_emplacement_key ON sonores (emplacement) WHERE supprime_le IS NULL;

COMMENT ON COLUMN sonores.crossfade_debut IS 'Crossfade de début ; NULL s''il n''est pas paramétré, 0 seconde en est un.';
COMMENT ON COLUMN sonores.crossfade_fin IS 'Crossfade de fin ; NULL s''il n''est pas paramétré, 0 seconde en est un.';
COMMENT ON COLUMN sonores.type_mime IS 'Type MIME du fichier lu par libmagic au dernier examen de l''indexeur ; NULL avant.';
COMMENT ON COLUMN sonores.verifie_le IS 'Dernière vérification complète du fichier par l''indexeur ; NULL avant.';
COMMENT ON COLUMN sonores.debut_detecte IS 'Silence au début du fichier, mesuré par l''audit complet ; NULL sans silence détecté.';
COMMENT ON COLUMN sonores.fin_detectee IS 'Silence à la fin du fichier, compté depuis sa fin ; NULL sans silence détecté.';
COMMENT ON COLUMN sonores.detection_silences IS 'Le sonore est joué sans ses silences détectés, même hors d''une banque qui les retire.';
COMMENT ON COLUMN sonores.audit_demande IS 'La prochaine indexation, même rapide, fait l''audit complet du sonore.';
COMMENT ON COLUMN sonores.audite_le IS 'Date du dernier audit complet du fichier, silences mesurés ; NULL jamais audité.';
COMMENT ON COLUMN sonores.audit_seuil IS 'Seuil de silence, en dB crête, du dernier audit complet ; NULL jamais audité.';
COMMENT ON COLUMN sonores.supprime_le IS 'Demande de suppression depuis l''interface ; NULL : pas supprimé.';
COMMENT ON COLUMN sonores.disparu_le IS 'Disparition du fichier, constatée par l''indexation (état supprime).';

CREATE TRIGGER sonores_modifie_le BEFORE UPDATE ON sonores
	FOR EACH ROW EXECUTE FUNCTION machincast_maj_modifie_le();

-- ─── Banques ───────────────────────────────────────────────

CREATE TABLE banques (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	-- Unique parmi les banques qui ne sont pas supprimées : voir banques_nom_interne_key.
	nom_interne varchar(255) NOT NULL,
	-- Affiché à la place de l'artiste et du titre masqués, après les noms publics de l'événement et de la séquence.
	nom_public varchar(255),
	mode mode_banque NOT NULL,
	masquer_metadonnees boolean,
	-- Une banque marquée ne passe jamais deux fois de suite, même d'un événement à l'autre (doc/spec.md § 4.4).
	ne_pas_repeter boolean NOT NULL DEFAULT false,
	modifie_le timestamptz NOT NULL DEFAULT clock_timestamp(),
	crossfade_debut_regle regle_crossfade NOT NULL DEFAULT 'sonore',
	crossfade_debut interval NOT NULL DEFAULT '0 s' CHECK (crossfade_debut >= '0 s'),
	crossfade_fin_regle regle_crossfade NOT NULL DEFAULT 'sonore',
	crossfade_fin interval NOT NULL DEFAULT '0 s' CHECK (crossfade_fin >= '0 s'),
	-- Durées hors desquelles un sonore de la banque est signalé, ou retiré par l'indexation
	-- (https://github.com/dascritch/machincast/issues/147, https://github.com/dascritch/machincast/issues/195).
	duree_min interval CHECK (duree_min > '0 s'),
	duree_max interval CHECK (duree_max > '0 s'),
	detection_silences boolean NOT NULL DEFAULT false,
	supprime_le timestamptz,
	CONSTRAINT banques_durees CHECK (duree_min <= duree_max)
);

CREATE UNIQUE INDEX banques_nom_interne_key ON banques (nom_interne) WHERE supprime_le IS NULL;

COMMENT ON COLUMN banques.crossfade_debut_regle IS 'Règle du crossfade de début des sonores joués via la banque.';
COMMENT ON COLUMN banques.crossfade_debut IS 'Crossfade de début de la banque, selon sa règle.';
COMMENT ON COLUMN banques.crossfade_fin_regle IS 'Règle du crossfade de fin des sonores joués via la banque.';
COMMENT ON COLUMN banques.crossfade_fin IS 'Crossfade de fin de la banque, selon sa règle.';
COMMENT ON COLUMN banques.duree_min IS 'Durée en deçà de laquelle un sonore de la banque est signalé ; NULL sans minimum.';
COMMENT ON COLUMN banques.duree_max IS 'Durée au-delà de laquelle un sonore de la banque est signalé ; NULL sans maximum.';
COMMENT ON COLUMN banques.detection_silences IS 'Les sonores joués via la banque le sont sans leurs silences détectés.';
COMMENT ON COLUMN banques.supprime_le IS 'Demande de suppression depuis l''interface ; NULL : pas supprimée.';

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
	-- Unique parmi les événements qui ne sont pas supprimés, comme les banques et les séquences : c'est leur nom dans
	-- les listes, le log et l'airplay (https://github.com/dascritch/machincast/issues/32).
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
	CONSTRAINT evenements_ordre CHECK (fin > debut),
	supprime_le timestamptz
);

CREATE UNIQUE INDEX evenements_nom_interne_key ON evenements (nom_interne) WHERE supprime_le IS NULL;

COMMENT ON COLUMN evenements.supprime_le IS 'Demande de suppression depuis l''interface ; NULL : pas supprimé.';

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

-- ─── Séquences ─────────────────────────────────────────────

-- Suites de sonores et de banques réutilisables dans les événements (doc/spec.md § 4.3).
CREATE TABLE sequences (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	-- Unique parmi les séquences qui ne sont pas supprimées : voir sequences_nom_interne_key.
	nom_interne varchar(255) NOT NULL,
	nom_public varchar(255),
	masquer_metadonnees boolean,
	modifie_le timestamptz NOT NULL DEFAULT clock_timestamp(),
	supprime_le timestamptz
);

CREATE UNIQUE INDEX sequences_nom_interne_key ON sequences (nom_interne) WHERE supprime_le IS NULL;

COMMENT ON COLUMN sequences.supprime_le IS 'Demande de suppression depuis l''interface ; NULL : pas supprimée.';

CREATE TRIGGER sequences_modifie_le BEFORE UPDATE ON sequences
	FOR EACH ROW EXECUTE FUNCTION machincast_maj_modifie_le();

-- Liste ordonnée d'une séquence : chaque élément est une banque ou un sonore, jamais une autre séquence, pour écarter
-- tout appel cyclique. Un même élément peut revenir plusieurs fois.
CREATE TABLE sequences_elements (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	sequence_id bigint NOT NULL REFERENCES sequences (id) ON DELETE CASCADE,
	position integer NOT NULL CHECK (position > 0),
	banque_id bigint REFERENCES banques (id) ON DELETE CASCADE,
	sonore_id bigint REFERENCES sonores (id) ON DELETE CASCADE,
	CONSTRAINT sequences_elements_banque_ou_sonore CHECK (num_nonnulls(banque_id, sonore_id) = 1),
	CONSTRAINT sequences_elements_position UNIQUE (sequence_id, position) DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX sequences_elements_banque ON sequences_elements (banque_id);
CREATE INDEX sequences_elements_sonore ON sequences_elements (sonore_id);

-- ─── Listes de lecture des événements ──────────────────────

-- Liste de lecture ordonnée d'un événement : chaque élément est une banque, un sonore ou une séquence.
-- Un même élément peut revenir plusieurs fois.
CREATE TABLE evenements_elements (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	evenement_id bigint NOT NULL REFERENCES evenements (id) ON DELETE CASCADE,
	position integer NOT NULL CHECK (position > 0),
	banque_id bigint REFERENCES banques (id) ON DELETE CASCADE,
	sonore_id bigint REFERENCES sonores (id) ON DELETE CASCADE,
	sequence_id bigint REFERENCES sequences (id) ON DELETE CASCADE,
	CONSTRAINT evenements_elements_un_element CHECK (num_nonnulls(banque_id, sonore_id, sequence_id) = 1),
	CONSTRAINT evenements_elements_position UNIQUE (evenement_id, position) DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX evenements_elements_banque ON evenements_elements (banque_id);
CREATE INDEX evenements_elements_sonore ON evenements_elements (sonore_id);
CREATE INDEX evenements_elements_sequence ON evenements_elements (sequence_id);

-- ─── Sessions sautées ──────────────────────────────────────
-- Une session d'un événement récurrent, à venir, peut être sautée depuis le calendrier de l'interface
-- (https://github.com/dascritch/machincast/issues/273). Elle se désigne par le jour où elle commence : un événement
-- récurrent n'en commence qu'une par jour, et le saut tient même si l'heure de l'événement change. Les sauts partent
-- avec leur événement, et la purge efface ceux d'avant la durée de péremption.

CREATE TABLE evenements_sauts (
	evenement_id bigint NOT NULL REFERENCES evenements (id) ON DELETE CASCADE,
	jour date NOT NULL,
	PRIMARY KEY (evenement_id, jour)
);

COMMENT ON TABLE evenements_sauts IS 'Sessions sautées d''un événement récurrent : le jour où chacune commence.';

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
	-- Pour un sonore joué par une séquence : la séquence et son élément, qui dit où la reprendre.
	sequence_id bigint REFERENCES sequences (id) ON DELETE SET NULL,
	sequence_element_id bigint REFERENCES sequences_elements (id) ON DELETE SET NULL,
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

GRANT SELECT ON sonores, feeds, banques, banques_sonores, evenements, evenements_elements, evenements_sauts, sequences,
	sequences_elements TO machincast_lecture;
GRANT UPDATE (etat) ON sonores TO machincast_lecture;
GRANT SELECT, INSERT ON airplay TO machincast_lecture;
GRANT INSERT ON log TO machincast_lecture;

-- ─── Machin_indexation ─────────────────────────────────────
-- Lit les banques et leurs répertoires, crée et met à jour les sonores, les rattache à leur banque.
-- Ne supprime aucun sonore : un fichier disparu fait passer son sonore à l'état supprime. Retire seulement d'une banque
-- les sonores dont la durée sort de ses limites (https://github.com/dascritch/machincast/issues/195).

GRANT SELECT, INSERT, UPDATE ON sonores TO machincast_indexation;
GRANT SELECT ON banques, banques_repertoires TO machincast_indexation;
GRANT SELECT, INSERT, DELETE ON banques_sonores TO machincast_indexation;

-- ─── Machin_interface ──────────────────────────────────────
-- Gère toute la programmation ; consulte l'airplay et le log sans pouvoir les modifier.

GRANT SELECT, INSERT, UPDATE, DELETE
	ON sonores, feeds, banques, banques_repertoires, banques_sonores, evenements, evenements_elements, sequences,
	sequences_elements
	TO machincast_interface;
GRANT SELECT, INSERT, DELETE ON evenements_sauts TO machincast_interface;
GRANT SELECT ON airplay, log TO machincast_interface;
