-- Les marques-pages de streams deviennent des feeds (https://github.com/dascritch/machincast/issues/252) : la table,
-- la colonne des sonores qui y renvoie, et les noms de leurs contraintes, index et séquence. Les droits des rôles
-- suivent la table renommée ; les données ne changent pas.
-- depends: 0011.sonores-dernier-audit

ALTER TABLE marques_pages_streams RENAME TO feeds;
ALTER TABLE feeds RENAME CONSTRAINT marques_pages_streams_pkey TO feeds_pkey;
ALTER TABLE feeds RENAME CONSTRAINT marques_pages_streams_nom_key TO feeds_nom_key;
ALTER SEQUENCE marques_pages_streams_id_seq RENAME TO feeds_id_seq;
ALTER TABLE sonores RENAME COLUMN marque_page_id TO feed_id;
ALTER TABLE sonores RENAME CONSTRAINT sonores_marque_page_id_fkey TO sonores_feed_id_fkey;

COMMENT ON TABLE feeds IS 'Feeds : adresses de streams nommées, qu''un sonore stream peut suivre (feed_id).';
