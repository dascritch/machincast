-- Type réel du fichier d'un sonore, lu par libmagic, et état des fichiers qui ne sont pas du son
-- (https://github.com/dascritch/machincast/issues/121).
-- depends: 0002.evenements-nom-unique

ALTER TYPE etat_sonore ADD VALUE 'non_supporte' AFTER 'errone';
ALTER TABLE sonores ADD COLUMN type_mime text;
COMMENT ON COLUMN sonores.type_mime IS 'Type MIME du fichier lu par libmagic au dernier examen de l''indexeur ; NULL avant.';
