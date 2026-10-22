-- Position des fondus d'une banque par rapport aux blancs détectés (https://github.com/dascritch/machincast/issues/234). NULL : celle des
-- préférences (crossfades.position_entree, crossfades.position_sortie). Le fade-in commence, est en cours ou se termine
-- au début détecté ; le fade-out, à la fin détectée. Seuls les sonores joués sans leurs blancs sont concernés.
-- depends: 0011.sonores-dernier-audit

CREATE TYPE position_fondu AS ENUM ('commence', 'en_cours', 'termine');

ALTER TABLE banques
	ADD COLUMN position_fondu_entree position_fondu,
	ADD COLUMN position_fondu_sortie position_fondu;

COMMENT ON COLUMN banques.position_fondu_entree IS 'Où le fade-in des sonores de la banque se place par rapport à leur début détecté ; NULL : selon les préférences.';
COMMENT ON COLUMN banques.position_fondu_sortie IS 'Où le fade-out des sonores de la banque se place par rapport à leur fin détectée ; NULL : selon les préférences.';
