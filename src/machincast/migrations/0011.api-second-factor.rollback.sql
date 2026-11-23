-- Annulation du second facteur et des navigateurs connus (https://github.com/dascritch/machincast/issues/601) : les
-- sessions qui attendent sans le pupitre ne se valideront plus.

UPDATE api_sessions SET state = 'invalid', code = NULL, ended_at = clock_timestamp()
	WHERE state = 'pending' AND (NOT desk OR totp);
ALTER TABLE api_sessions DROP COLUMN totp;
ALTER TABLE api_sessions DROP COLUMN desk;
DROP TABLE api_browsers;
ALTER TABLE api_users DROP COLUMN totp_secret;
