-- Annulation du renommage des marques-pages de streams en feeds (https://github.com/dascritch/machincast/issues/252).

COMMENT ON TABLE feeds IS NULL;
ALTER TABLE sonores RENAME CONSTRAINT sonores_feed_id_fkey TO sonores_marque_page_id_fkey;
ALTER TABLE sonores RENAME COLUMN feed_id TO marque_page_id;
ALTER SEQUENCE feeds_id_seq RENAME TO marques_pages_streams_id_seq;
ALTER TABLE feeds RENAME CONSTRAINT feeds_nom_key TO marques_pages_streams_nom_key;
ALTER TABLE feeds RENAME CONSTRAINT feeds_pkey TO marques_pages_streams_pkey;
ALTER TABLE feeds RENAME TO marques_pages_streams;
