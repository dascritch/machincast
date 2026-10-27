-- Sessions sautées (https://github.com/dascritch/machincast/issues/273) : une session d'un événement récurrent, à
-- venir, peut être sautée depuis le calendrier de l'interface, pour des vacances par exemple. Une session se désigne
-- par le jour où elle commence : un événement récurrent n'en commence qu'une par jour, et le saut tient même si
-- l'heure de l'événement change. Sautée, elle ne joue pas ; elle se rétablit depuis le calendrier. Les sauts partent
-- avec leur événement, et la purge efface ceux d'avant la durée de péremption.
-- depends: 0013.suppression-differee

CREATE TABLE evenements_sauts (
	evenement_id bigint NOT NULL REFERENCES evenements (id) ON DELETE CASCADE,
	jour date NOT NULL,
	PRIMARY KEY (evenement_id, jour)
);

COMMENT ON TABLE evenements_sauts IS 'Sessions sautées d''un événement récurrent : le jour où chacune commence.';

GRANT SELECT ON evenements_sauts TO machincast_lecture;
GRANT SELECT, INSERT, DELETE ON evenements_sauts TO machincast_interface;
