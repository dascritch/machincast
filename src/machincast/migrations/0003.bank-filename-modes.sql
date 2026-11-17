-- Les banques dans l'ordre du nom de fichier de leurs sonores, de A à Z ou de Z à A
-- (https://github.com/dascritch/machincast/issues/454) : comme le mode séquentiel, mais dans l'ordre du nom de fichier,
-- sans son répertoire, au lieu de l'ordre des positions.

ALTER TYPE bank_mode ADD VALUE 'filename_ascending';
ALTER TYPE bank_mode ADD VALUE 'filename_descending';
