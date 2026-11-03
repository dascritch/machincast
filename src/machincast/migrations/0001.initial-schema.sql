-- Schéma initial de MachinCast. Référence : doc/fr/spec.md § 3.1 (tables) et § 3.2 (rôles et droits).
--
-- Réunit, avant que le projet serve réellement, toutes les migrations d'avant
-- (https://github.com/dascritch/machincast/issues/314), puis réécrit avec des noms anglais
-- (https://github.com/dascritch/machincast/issues/358) : une base créée avec l'ancien schéma, en français
-- (0001.schema-initial), se recrée ; machincast.base.SchemaPerime la refuse.
--
-- Textes saisis à la main (noms, artiste, titre, nature) : varchar(255), même limite que l'interface.
-- Chemins, URL et messages détaillés : text, leur longueur n'est pas bornée à l'avance.

-- ─── Types énumérés ────────────────────────────────────────
-- L'ordre de déclaration compte : il permet de comparer et de trier les valeurs.

CREATE TYPE sound_type AS ENUM ('file', 'stream');
CREATE TYPE bank_mode AS ENUM ('sequential', 'random');
-- Ordre croissant de priorité : background_programming (fil musical) < show (émission) < special. La priorité
-- fallback (secours), rangée en dessous, est hors grille : un événement de secours ne joue qu'à la place d'un stream
-- tombé (doc/fr/spec.md § 4.7).
CREATE TYPE event_priority AS ENUM ('fallback', 'background_programming', 'show', 'special');
CREATE TYPE weekday AS ENUM ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday');
CREATE TYPE airplay_line_type AS ENUM ('start', 'end');
CREATE TYPE log_level AS ENUM ('info', 'warning', 'incident');
-- État d'un sonore, dans l'ordre de sa vie (doc/fr/spec.md § 3.1) :
--   preview      aperçu : nouveau fichier, enregistré sans être décodé ; pas jouable ;
--   active       actif : jouable ;
--   disabled     désactivé : retiré par l'interface, choix humain ;
--   expired      expiré : retiré par Machin player, maximum de lectures atteint ou fin de la période de diffusion ;
--   corrupt      erroné : fichier illisible ou endommagé, posé par l'indexeur, qui le rétablit si le fichier redevient
--                sain ;
--   unsupported  non supporté : fichier qui n'est pas du son, d'après son type lu par libmagic
--                (https://github.com/dascritch/machincast/issues/121) ;
--   missing      supprimé : fichier introuvable, posé par l'indexeur.
-- L'interface les affiche en français.
CREATE TYPE sound_state AS ENUM ('preview', 'active', 'disabled', 'expired', 'corrupt', 'unsupported', 'missing');
-- Crossfades d'une banque, pour les sonores qu'elle fait jouer (https://github.com/dascritch/machincast/issues/143) :
-- « sound » garde le crossfade du sonore, « default » donne celui de la banque à un sonore qui n'en a pas de
-- paramétré, « forced » donne celui de la banque à tout sonore.
CREATE TYPE crossfade_rule AS ENUM ('sound', 'default', 'forced');

-- Mise à jour automatique de la colonne modified_at.
CREATE FUNCTION machincast_set_modified_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
	NEW.modified_at := clock_timestamp();
	RETURN NEW;
END;
$$;

-- ─── Feeds ─────────────────────────────────────────────────
-- Adresses de streams nommées, qu'un sonore stream peut suivre (https://github.com/dascritch/machincast/issues/252).

CREATE TABLE feeds (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	name varchar(255) NOT NULL UNIQUE,
	url text NOT NULL
);

COMMENT ON TABLE feeds IS 'Feeds : adresses de streams nommées, qu''un sonore stream peut suivre (feed_id).';

-- ─── Sonores ───────────────────────────────────────────────

CREATE TABLE sounds (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	type sound_type NOT NULL,
	-- Unique parmi les sonores qui ne sont pas supprimés : voir sounds_location_key.
	location text,
	stream_url text,
	feed_id bigint REFERENCES feeds (id) ON DELETE RESTRICT,
	-- Stream seulement : événement de secours joué quand le flux tombe ; vide, l'événement de priorité inférieure.
	-- Sa clé étrangère est posée après la table events.
	fallback_event_id bigint,
	-- Artiste et titre servent au masquage, à la recherche et à l'airplay : ce sont des colonnes.
	artist varchar(255),
	title varchar(255),
	-- Métadonnées non critiques (année, label, genre…), libres et extensibles sans migration.
	music_metadata jsonb NOT NULL DEFAULT '{}'
		CHECK (jsonb_typeof(music_metadata) = 'object'),
	-- NULL : pas paramétré, celui de la banque ou de la configuration ; 0 seconde en est un
	-- (https://github.com/dascritch/machincast/issues/145).
	crossfade_start interval CHECK (crossfade_start >= '0 s'),
	crossfade_end interval CHECK (crossfade_end >= '0 s'),
	max_plays integer CHECK (max_plays > 0),
	state sound_state NOT NULL DEFAULT 'active',
	hide_metadata boolean,
	duration interval CHECK (duration > '0 s'),
	broadcast_start timestamptz,
	broadcast_end timestamptz,
	file_modified_at timestamptz,
	file_size bigint CHECK (file_size >= 0),
	edited_fields text[] NOT NULL DEFAULT '{}',
	indexed_at timestamptz,
	modified_at timestamptz NOT NULL DEFAULT clock_timestamp(),
	-- Type réel du fichier, lu par libmagic (https://github.com/dascritch/machincast/issues/121).
	mime_type text,
	-- Dernière vérification complète du fichier : son type lu, puis son décodage
	-- (https://github.com/dascritch/machincast/issues/125).
	checked_at timestamptz,
	-- Silences au début et à la fin du fichier, mesurés par l'audit complet ; la fin détectée se compte depuis la fin
	-- du fichier. Le fichier n'est jamais touché (https://github.com/dascritch/machincast/issues/146).
	detected_start interval CHECK (detected_start >= '0 s'),
	detected_end interval CHECK (detected_end >= '0 s'),
	silence_detection boolean NOT NULL DEFAULT false,
	-- La prochaine indexation, même rapide, fait l'audit complet du sonore
	-- (https://github.com/dascritch/machincast/issues/114).
	audit_requested boolean NOT NULL DEFAULT false,
	-- Dernier audit complet, et son seuil de silence (https://github.com/dascritch/machincast/issues/206).
	audited_at timestamptz,
	audit_threshold double precision CHECK (audit_threshold >= -100 AND audit_threshold < 0),
	-- Suppression différée (https://github.com/dascritch/machincast/issues/267) : demandée depuis l'interface, ou
	-- disparition du fichier constatée par l'indexation (état missing).
	deleted_at timestamptz,
	missing_at timestamptz,
	CONSTRAINT sounds_file_or_stream CHECK (
		(type = 'file' AND location IS NOT NULL AND stream_url IS NULL AND feed_id IS NULL)
		OR (type = 'stream' AND location IS NULL AND num_nonnulls(stream_url, feed_id) = 1)
	),
	CONSTRAINT sounds_file_duration CHECK (type = 'file' OR duration IS NULL),
	CONSTRAINT sounds_broadcast_period CHECK (broadcast_end > broadcast_start),
	CONSTRAINT sounds_audit CHECK ((audited_at IS NULL) = (audit_threshold IS NULL))
);

-- Un élément supprimé ne garde ni son nom ni son emplacement : l'unicité ne vaut que pour ceux qui ne le sont pas
-- (https://github.com/dascritch/machincast/issues/267).
CREATE UNIQUE INDEX sounds_location_key ON sounds (location) WHERE deleted_at IS NULL;

COMMENT ON COLUMN sounds.crossfade_start IS 'Crossfade de début ; NULL s''il n''est pas paramétré, 0 seconde en est un.';
COMMENT ON COLUMN sounds.crossfade_end IS 'Crossfade de fin ; NULL s''il n''est pas paramétré, 0 seconde en est un.';
COMMENT ON COLUMN sounds.mime_type IS 'Type MIME du fichier lu par libmagic au dernier examen de l''indexeur ; NULL avant.';
COMMENT ON COLUMN sounds.checked_at IS 'Dernière vérification complète du fichier par l''indexeur ; NULL avant.';
COMMENT ON COLUMN sounds.detected_start IS 'Silence au début du fichier, mesuré par l''audit complet ; NULL sans silence détecté.';
COMMENT ON COLUMN sounds.detected_end IS 'Silence à la fin du fichier, compté depuis sa fin ; NULL sans silence détecté.';
COMMENT ON COLUMN sounds.silence_detection IS 'Le sonore est joué sans ses silences détectés, même hors d''une banque qui les retire.';
COMMENT ON COLUMN sounds.audit_requested IS 'La prochaine indexation, même rapide, fait l''audit complet du sonore.';
COMMENT ON COLUMN sounds.audited_at IS 'Date du dernier audit complet du fichier, silences mesurés ; NULL jamais audité.';
COMMENT ON COLUMN sounds.audit_threshold IS 'Seuil de silence, en dB crête, du dernier audit complet ; NULL jamais audité.';
COMMENT ON COLUMN sounds.deleted_at IS 'Demande de suppression depuis l''interface ; NULL : pas supprimé.';
COMMENT ON COLUMN sounds.missing_at IS 'Disparition du fichier, constatée par l''indexation (état missing).';

CREATE TRIGGER sounds_modified_at BEFORE UPDATE ON sounds
	FOR EACH ROW EXECUTE FUNCTION machincast_set_modified_at();

-- ─── Banques ───────────────────────────────────────────────

CREATE TABLE banks (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	-- Unique parmi les banques qui ne sont pas supprimées : voir banks_internal_name_key.
	internal_name varchar(255) NOT NULL,
	-- Affiché à la place de l'artiste et du titre masqués, après les noms publics de l'événement et de la séquence.
	public_name varchar(255),
	mode bank_mode NOT NULL,
	hide_metadata boolean,
	-- Une banque marquée ne passe jamais deux fois de suite, même d'un événement à l'autre (doc/fr/spec.md § 4.4).
	no_repeat boolean NOT NULL DEFAULT false,
	modified_at timestamptz NOT NULL DEFAULT clock_timestamp(),
	crossfade_start_rule crossfade_rule NOT NULL DEFAULT 'sound',
	crossfade_start interval NOT NULL DEFAULT '0 s' CHECK (crossfade_start >= '0 s'),
	crossfade_end_rule crossfade_rule NOT NULL DEFAULT 'sound',
	crossfade_end interval NOT NULL DEFAULT '0 s' CHECK (crossfade_end >= '0 s'),
	-- Durées hors desquelles un sonore de la banque est signalé, ou retiré par l'indexation
	-- (https://github.com/dascritch/machincast/issues/147, https://github.com/dascritch/machincast/issues/195).
	min_duration interval CHECK (min_duration > '0 s'),
	max_duration interval CHECK (max_duration > '0 s'),
	silence_detection boolean NOT NULL DEFAULT false,
	deleted_at timestamptz,
	CONSTRAINT banks_durations CHECK (min_duration <= max_duration)
);

CREATE UNIQUE INDEX banks_internal_name_key ON banks (internal_name) WHERE deleted_at IS NULL;

COMMENT ON COLUMN banks.crossfade_start_rule IS 'Règle du crossfade de début des sonores joués via la banque.';
COMMENT ON COLUMN banks.crossfade_start IS 'Crossfade de début de la banque, selon sa règle.';
COMMENT ON COLUMN banks.crossfade_end_rule IS 'Règle du crossfade de fin des sonores joués via la banque.';
COMMENT ON COLUMN banks.crossfade_end IS 'Crossfade de fin de la banque, selon sa règle.';
COMMENT ON COLUMN banks.min_duration IS 'Durée en deçà de laquelle un sonore de la banque est signalé ; NULL sans minimum.';
COMMENT ON COLUMN banks.max_duration IS 'Durée au-delà de laquelle un sonore de la banque est signalé ; NULL sans maximum.';
COMMENT ON COLUMN banks.silence_detection IS 'Les sonores joués via la banque le sont sans leurs silences détectés.';
COMMENT ON COLUMN banks.deleted_at IS 'Demande de suppression depuis l''interface ; NULL : pas supprimée.';

CREATE TRIGGER banks_modified_at BEFORE UPDATE ON banks
	FOR EACH ROW EXECUTE FUNCTION machincast_set_modified_at();

-- Répertoires indexés d'une banque : une banque peut en avoir plusieurs,
-- et un même répertoire peut alimenter plusieurs banques.
CREATE TABLE bank_directories (
	bank_id bigint NOT NULL REFERENCES banks (id) ON DELETE CASCADE,
	directory text NOT NULL,
	PRIMARY KEY (bank_id, directory)
);

CREATE INDEX bank_directories_directory ON bank_directories (directory);

-- Un sonore figure au plus une fois dans une banque ; il peut appartenir à plusieurs banques.
-- L'unicité des positions est différée à la fin de la transaction, pour permettre de réordonner.
CREATE TABLE bank_sounds (
	bank_id bigint NOT NULL REFERENCES banks (id) ON DELETE CASCADE,
	sound_id bigint NOT NULL REFERENCES sounds (id) ON DELETE CASCADE,
	position integer NOT NULL CHECK (position > 0),
	PRIMARY KEY (bank_id, sound_id),
	CONSTRAINT bank_sounds_position UNIQUE (bank_id, position) DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX bank_sounds_sound ON bank_sounds (sound_id);

-- ─── Événements ────────────────────────────────────────────

CREATE TABLE events (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	-- Unique parmi les événements qui ne sont pas supprimés, comme les banques et les séquences : c'est leur nom dans
	-- les listes, le log et l'airplay (https://github.com/dascritch/machincast/issues/32).
	internal_name varchar(255) NOT NULL,
	public_name varchar(255),
	priority event_priority NOT NULL,
	starts_at timestamptz,
	ends_at timestamptz,
	-- Jours de la semaine où l'événement se répète. Vide = pas de récurrence.
	recurrence_days weekday[] NOT NULL DEFAULT '{}',
	hide_metadata boolean,
	modified_at timestamptz NOT NULL DEFAULT clock_timestamp(),
	-- Seuls un fil musical (fil permanent) et un événement de secours peuvent n'avoir aucune date de début.
	CONSTRAINT events_start CHECK (starts_at IS NOT NULL OR priority IN ('background_programming', 'fallback')),
	-- Un événement de secours est hors grille : ni début, ni fin, ni jours de récurrence.
	CONSTRAINT events_fallback_off_grid
		CHECK (priority <> 'fallback' OR (starts_at IS NULL AND ends_at IS NULL AND recurrence_days = '{}')),
	-- Pas de fin sans début.
	CONSTRAINT events_end_without_start CHECK (ends_at IS NULL OR starts_at IS NOT NULL),
	CONSTRAINT events_order CHECK (ends_at > starts_at),
	deleted_at timestamptz
);

CREATE UNIQUE INDEX events_internal_name_key ON events (internal_name) WHERE deleted_at IS NULL;

COMMENT ON COLUMN events.deleted_at IS 'Demande de suppression depuis l''interface ; NULL : pas supprimé.';

CREATE TRIGGER events_modified_at BEFORE UPDATE ON events
	FOR EACH ROW EXECUTE FUNCTION machincast_set_modified_at();

-- Événement de secours d'un stream. Un événement supprimé laisse le stream sans secours.
ALTER TABLE sounds
	ADD CONSTRAINT sounds_fallback_event
		FOREIGN KEY (fallback_event_id) REFERENCES events (id) ON DELETE SET NULL,
	ADD CONSTRAINT sounds_fallback_stream CHECK (type = 'stream' OR fallback_event_id IS NULL);

CREATE INDEX sounds_fallback_event ON sounds (fallback_event_id);

-- Le secours d'un stream est toujours un événement de priorité fallback : vérifié à l'enregistrement du sonore,
-- et quand la priorité d'un événement désigné change. Conditions imbriquées : la requête sur l'autre table n'est
-- préparée que lorsqu'elle est nécessaire ; l'indexeur, qui enregistre des fichiers sans droit de lire les
-- événements, ne la déclenche jamais.
CREATE FUNCTION machincast_check_sound_fallback() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
	IF NEW.fallback_event_id IS NOT NULL THEN
		IF NOT EXISTS (SELECT 1 FROM events WHERE id = NEW.fallback_event_id AND priority = 'fallback') THEN
			RAISE EXCEPTION 'l''événement % n''est pas un événement de secours', NEW.fallback_event_id
				USING ERRCODE = 'check_violation';
		END IF;
	END IF;
	RETURN NEW;
END;
$$;

CREATE TRIGGER sounds_fallback BEFORE INSERT OR UPDATE OF fallback_event_id ON sounds
	FOR EACH ROW EXECUTE FUNCTION machincast_check_sound_fallback();

CREATE FUNCTION machincast_check_event_fallback() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
	IF OLD.priority = 'fallback' AND NEW.priority <> 'fallback' THEN
		IF EXISTS (SELECT 1 FROM sounds WHERE fallback_event_id = NEW.id) THEN
			RAISE EXCEPTION 'l''événement % sert de secours à un stream : il reste de priorité secours', NEW.id
				USING ERRCODE = 'check_violation';
		END IF;
	END IF;
	RETURN NEW;
END;
$$;

CREATE TRIGGER events_fallback BEFORE UPDATE OF priority ON events
	FOR EACH ROW EXECUTE FUNCTION machincast_check_event_fallback();

-- ─── Séquences ─────────────────────────────────────────────

-- Suites de sonores et de banques réutilisables dans les événements (doc/fr/spec.md § 4.3).
CREATE TABLE sequences (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	-- Unique parmi les séquences qui ne sont pas supprimées : voir sequences_internal_name_key.
	internal_name varchar(255) NOT NULL,
	public_name varchar(255),
	hide_metadata boolean,
	modified_at timestamptz NOT NULL DEFAULT clock_timestamp(),
	deleted_at timestamptz
);

CREATE UNIQUE INDEX sequences_internal_name_key ON sequences (internal_name) WHERE deleted_at IS NULL;

COMMENT ON COLUMN sequences.deleted_at IS 'Demande de suppression depuis l''interface ; NULL : pas supprimée.';

CREATE TRIGGER sequences_modified_at BEFORE UPDATE ON sequences
	FOR EACH ROW EXECUTE FUNCTION machincast_set_modified_at();

-- Liste ordonnée d'une séquence : chaque élément est une banque ou un sonore, jamais une autre séquence, pour écarter
-- tout appel cyclique. Un même élément peut revenir plusieurs fois.
CREATE TABLE sequence_items (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	sequence_id bigint NOT NULL REFERENCES sequences (id) ON DELETE CASCADE,
	position integer NOT NULL CHECK (position > 0),
	bank_id bigint REFERENCES banks (id) ON DELETE CASCADE,
	sound_id bigint REFERENCES sounds (id) ON DELETE CASCADE,
	CONSTRAINT sequence_items_bank_or_sound CHECK (num_nonnulls(bank_id, sound_id) = 1),
	CONSTRAINT sequence_items_position UNIQUE (sequence_id, position) DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX sequence_items_bank ON sequence_items (bank_id);
CREATE INDEX sequence_items_sound ON sequence_items (sound_id);

-- ─── Listes de lecture des événements ──────────────────────

-- Liste de lecture ordonnée d'un événement : chaque élément est une banque, un sonore ou une séquence.
-- Un même élément peut revenir plusieurs fois.
CREATE TABLE event_items (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	event_id bigint NOT NULL REFERENCES events (id) ON DELETE CASCADE,
	position integer NOT NULL CHECK (position > 0),
	bank_id bigint REFERENCES banks (id) ON DELETE CASCADE,
	sound_id bigint REFERENCES sounds (id) ON DELETE CASCADE,
	sequence_id bigint REFERENCES sequences (id) ON DELETE CASCADE,
	CONSTRAINT event_items_one_item CHECK (num_nonnulls(bank_id, sound_id, sequence_id) = 1),
	CONSTRAINT event_items_position UNIQUE (event_id, position) DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX event_items_bank ON event_items (bank_id);
CREATE INDEX event_items_sound ON event_items (sound_id);
CREATE INDEX event_items_sequence ON event_items (sequence_id);

-- ─── Sessions sautées ──────────────────────────────────────
-- Une session d'un événement récurrent, à venir, peut être sautée depuis le calendrier de l'interface
-- (https://github.com/dascritch/machincast/issues/273). Elle se désigne par le jour où elle commence : un événement
-- récurrent n'en commence qu'une par jour, et le saut tient même si l'heure de l'événement change. Les sauts partent
-- avec leur événement, et la purge efface ceux d'avant la durée de péremption.

CREATE TABLE event_skips (
	event_id bigint NOT NULL REFERENCES events (id) ON DELETE CASCADE,
	day date NOT NULL,
	PRIMARY KEY (event_id, day)
);

COMMENT ON TABLE event_skips IS 'Sessions sautées d''un événement récurrent : le jour où chacune commence.';

-- ─── Airplay ───────────────────────────────────────────────

-- Historique de diffusion : une ligne au début et une ligne à la fin de chaque passage.
-- Les lignes ne sont jamais supprimées ; les références passent à NULL quand l'élément est supprimé,
-- et l'emplacement (chemin ou URL), l'artiste et le titre sont recopiés au moment du passage.
CREATE TABLE airplay (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	play_id uuid NOT NULL,
	line_type airplay_line_type NOT NULL,
	logged_at timestamptz NOT NULL DEFAULT clock_timestamp(),
	sound_id bigint REFERENCES sounds (id) ON DELETE SET NULL,
	bank_id bigint REFERENCES banks (id) ON DELETE SET NULL,
	event_id bigint REFERENCES events (id) ON DELETE SET NULL,
	-- Élément de la liste qui a fait jouer le passage : un même élément peut figurer plusieurs fois dans une liste,
	-- seul lui dit où la reprendre, à l'élément qui suit le dernier joué.
	event_item_id bigint REFERENCES event_items (id) ON DELETE SET NULL,
	-- Pour un sonore joué par une séquence : la séquence et son élément, qui dit où la reprendre.
	sequence_id bigint REFERENCES sequences (id) ON DELETE SET NULL,
	sequence_item_id bigint REFERENCES sequence_items (id) ON DELETE SET NULL,
	location text,
	artist varchar(255),
	title varchar(255),
	played_duration interval CHECK (played_duration >= '0 s'),
	without_incident boolean,
	CONSTRAINT airplay_one_start_one_end UNIQUE (play_id, line_type),
	CONSTRAINT airplay_end_fields CHECK (
		(line_type = 'start' AND played_duration IS NULL AND without_incident IS NULL)
		OR (line_type = 'end' AND played_duration IS NOT NULL AND without_incident IS NOT NULL)
	)
);

CREATE INDEX airplay_logged_at ON airplay (logged_at);
CREATE INDEX airplay_bank ON airplay (bank_id, logged_at);
CREATE INDEX airplay_sound ON airplay (sound_id, logged_at);
CREATE INDEX airplay_event ON airplay (event_id, logged_at);

-- ─── Log ───────────────────────────────────────────────────

CREATE TABLE log (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	logged_at timestamptz NOT NULL DEFAULT clock_timestamp(),
	level log_level NOT NULL,
	kind varchar(255) NOT NULL,
	message text NOT NULL DEFAULT '',
	sound_id bigint REFERENCES sounds (id) ON DELETE SET NULL,
	bank_id bigint REFERENCES banks (id) ON DELETE SET NULL,
	event_id bigint REFERENCES events (id) ON DELETE SET NULL
);

CREATE INDEX log_logged_at ON log (logged_at);
CREATE INDEX log_incidents ON log (logged_at) WHERE level <> 'info';

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
	FOREACH role IN ARRAY ARRAY['machincast_player', 'machincast_indexer', 'machincast_interface'] LOOP
		IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = role) THEN
			EXECUTE format('CREATE ROLE %I NOLOGIN', role);
		END IF;
	END LOOP;
END;
$$;

GRANT USAGE ON SCHEMA public TO machincast_player, machincast_indexer, machincast_interface;

-- ─── Machin_player ────────────────────────────────────────
-- Lit la programmation, passe les sonores à l'état expired (colonne state seule), écrit l'airplay et le log.
-- Pas de lecture du log : une insertion dans log ne doit pas utiliser RETURNING.

GRANT SELECT ON sounds, feeds, banks, bank_sounds, events, event_items, event_skips, sequences,
	sequence_items TO machincast_player;
GRANT UPDATE (state) ON sounds TO machincast_player;
GRANT SELECT, INSERT ON airplay TO machincast_player;
GRANT INSERT ON log TO machincast_player;

-- ─── Machin_indexer ─────────────────────────────────────
-- Lit les banques et leurs répertoires, crée et met à jour les sonores, les rattache à leur banque.
-- Ne supprime aucun sonore : un fichier disparu fait passer son sonore à l'état missing. Retire seulement d'une banque
-- les sonores dont la durée sort de ses limites (https://github.com/dascritch/machincast/issues/195).

GRANT SELECT, INSERT, UPDATE ON sounds TO machincast_indexer;
GRANT SELECT ON banks, bank_directories TO machincast_indexer;
GRANT SELECT, INSERT, DELETE ON bank_sounds TO machincast_indexer;

-- ─── Machin_interface ──────────────────────────────────────
-- Gère toute la programmation ; consulte l'airplay et le log sans pouvoir les modifier.

GRANT SELECT, INSERT, UPDATE, DELETE
	ON sounds, feeds, banks, bank_directories, bank_sounds, events, event_items, sequences,
	sequence_items
	TO machincast_interface;
GRANT SELECT, INSERT, DELETE ON event_skips TO machincast_interface;
GRANT SELECT ON airplay, log TO machincast_interface;
