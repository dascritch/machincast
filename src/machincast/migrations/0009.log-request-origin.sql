-- D'où vient une action d'antenne consignée au log, et qui l'a faite (https://github.com/dascritch/machincast/issues/549).
-- Machin player reçoit les demandes de l'interface sur sa socket d'état, et celles du serveur intranet sur la socket
-- qu'il lui réserve, où chaque demande nomme le compte de l'API qui la fait. Le nom reste, même le compte supprimé.

CREATE TYPE request_origin AS ENUM ('interface', 'intranet');

ALTER TABLE log
	ADD COLUMN origin request_origin,
	ADD COLUMN api_user varchar(255),
	ADD CONSTRAINT log_api_user_from_intranet CHECK ((api_user IS NULL) OR (origin = 'intranet'));
