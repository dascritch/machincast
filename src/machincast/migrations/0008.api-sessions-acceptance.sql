-- La connexion à distance acceptée au pupitre avant que son code soit donné
-- (https://github.com/dascritch/machincast/issues/547).
-- L'interface montre d'abord qui demande à se connecter, d'où et avec quel navigateur ; le code à 6 chiffres
-- n'apparaît qu'une fois la connexion acceptée, et aucun code n'est essayé avant. Seule l'interface accepte : le
-- serveur intranet, exposé au réseau, ne modifie que les colonnes de la validation.

ALTER TABLE api_sessions ADD COLUMN accepted_at timestamptz;

REVOKE UPDATE ON api_sessions FROM machincast_intranet;
GRANT UPDATE (state, code, attempts, validated_at, expires_at, ended_at) ON api_sessions TO machincast_intranet;
