-- Les couleurs des émissions (https://github.com/dascritch/machincast/issues/628) : les genres, chacun avec sa
-- couleur, et la couleur de chaque priorité de la grille qui a des émissions. Le genre d'un événement est dans sa
-- colonne properties, sous la clé du plugin : {"color_the_shows": {"genre": <identifiant>}}.

CREATE TABLE color_the_shows__genres (
	id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	name varchar(64) NOT NULL UNIQUE CHECK (btrim(name) <> ''),
	colour char(7) NOT NULL CHECK (colour ~ '^#[0-9a-f]{6}$')
);

COMMENT ON TABLE color_the_shows__genres IS 'Les genres d''émissions, et leur couleur dans le calendrier et l''airplay.';

CREATE TABLE color_the_shows__priorities (
	priority event_priority PRIMARY KEY CHECK (priority IN ('background_programming', 'show', 'special')),
	colour char(7) NOT NULL CHECK (colour ~ '^#[0-9a-f]{6}$')
);

COMMENT ON TABLE color_the_shows__priorities IS 'La couleur de chaque priorité, pour un événement sans genre.';

-- Gris pour le fil antenne, vert pour les émissions, rouge pour les spéciales.
INSERT INTO color_the_shows__priorities (priority, colour) VALUES
	('background_programming', '#b4b4b4'),
	('show', '#8fd19e'),
	('special', '#f08c8c');

INSERT INTO color_the_shows__genres (name, colour) VALUES
	('talk', '#f2c14e'),
	('jazz', '#5b8def'),
	('metal', '#3d3d3d'),
	('reggae', '#e07b39');

GRANT SELECT ON color_the_shows__genres, color_the_shows__priorities TO machincast_intranet;
GRANT SELECT, INSERT, UPDATE, DELETE ON color_the_shows__genres, color_the_shows__priorities TO machincast_interface;
