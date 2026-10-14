-- Schéma initial de MachinCast (ticket #3). Référence : doc/spec.md § 3.1.

-- ─── Types énumérés ────────────────────────────────────────
-- L'ordre de déclaration compte : il permet de comparer et de trier les valeurs.

CREATE TYPE type_sonore AS ENUM ('fichier', 'stream');
CREATE TYPE mode_banque AS ENUM ('sequentiel', 'aleatoire');
-- Ordre croissant de priorité : fil_musical < emission < special.
CREATE TYPE priorite_evenement AS ENUM ('fil_musical', 'emission', 'special');
CREATE TYPE jour_semaine AS ENUM ('lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche');
CREATE TYPE type_ligne_airplay AS ENUM ('debut', 'fin');
CREATE TYPE niveau_log AS ENUM ('info', 'alerte', 'incident');

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
	nom text NOT NULL UNIQUE,
	url text NOT NULL
);

-- ─── Sonores ───────────────────────────────────────────────

CREATE TABLE sonores (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	type type_sonore NOT NULL,
	emplacement text UNIQUE,
	url_stream text,
	marque_page_id bigint REFERENCES marques_pages_streams (id) ON DELETE RESTRICT,
	-- Artiste et titre servent au masquage, à la recherche et à l'airplay : ce sont des colonnes.
	artiste text,
	titre text,
	-- Métadonnées non critiques (année, label, genre…), libres et extensibles sans migration.
	metadonnees_musicales jsonb NOT NULL DEFAULT '{}'
		CHECK (jsonb_typeof(metadonnees_musicales) = 'object'),
	crossfade_debut interval NOT NULL DEFAULT '0 s' CHECK (crossfade_debut >= '0 s'),
	crossfade_fin interval NOT NULL DEFAULT '0 s' CHECK (crossfade_fin >= '0 s'),
	max_lectures integer CHECK (max_lectures > 0),
	actif boolean NOT NULL DEFAULT true,
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
	nom_interne text NOT NULL UNIQUE,
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
	nom_interne text NOT NULL,
	nom_public text,
	priorite priorite_evenement NOT NULL,
	debut timestamptz,
	fin timestamptz,
	-- Jours de la semaine où l'événement se répète. Vide = pas de récurrence.
	jours_recurrence jour_semaine[] NOT NULL DEFAULT '{}',
	masquer_metadonnees boolean,
	modifie_le timestamptz NOT NULL DEFAULT clock_timestamp(),
	-- Seul un fil musical peut n'avoir aucune date de début (fil permanent).
	CONSTRAINT evenements_debut CHECK (debut IS NOT NULL OR priorite = 'fil_musical'),
	-- Pas de fin sans début.
	CONSTRAINT evenements_fin_sans_debut CHECK (fin IS NULL OR debut IS NOT NULL),
	CONSTRAINT evenements_ordre CHECK (fin > debut)
);

CREATE TRIGGER evenements_modifie_le BEFORE UPDATE ON evenements
	FOR EACH ROW EXECUTE FUNCTION machincast_maj_modifie_le();

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
	emplacement text,
	artiste text,
	titre text,
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
	nature text NOT NULL,
	message text NOT NULL DEFAULT '',
	sonore_id bigint REFERENCES sonores (id) ON DELETE SET NULL,
	banque_id bigint REFERENCES banques (id) ON DELETE SET NULL,
	evenement_id bigint REFERENCES evenements (id) ON DELETE SET NULL
);

CREATE INDEX log_horodatage ON log (horodatage);
CREATE INDEX log_incidents ON log (horodatage) WHERE niveau <> 'info';
