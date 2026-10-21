-- L'indexation retire d'une banque les sonores dont la durée sort de ses limites
-- (https://github.com/dascritch/machincast/issues/195) : elle ne supprime que la ligne de banques_sonores, jamais le
-- sonore ni son fichier.
-- depends: 0009.sonores-audit-demande

GRANT DELETE ON banques_sonores TO machincast_indexation;
