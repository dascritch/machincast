-- Annulation de l'origine des actions d'antenne au log (https://github.com/dascritch/machincast/issues/549).

ALTER TABLE log DROP CONSTRAINT log_api_user_from_intranet, DROP COLUMN api_user, DROP COLUMN origin;
DROP TYPE request_origin;
