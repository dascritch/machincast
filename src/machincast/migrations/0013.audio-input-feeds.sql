-- Les feeds d'entrée audio (https://github.com/dascritch/machincast/issues/623, ticket enfant de
-- https://github.com/dascritch/machincast/issues/513). Un feed est d'un genre : adresse, un stream comme avant, ou
-- entrée audio, qui porte le périphérique d'une entrée de audio.inputs à la place de l'adresse. Ses streams se jouent
-- en captant l'entrée ; leur adresse est alors « input: » suivi du périphérique (machincast.audio.INPUT_ADDRESS).

ALTER TABLE feeds ALTER COLUMN url DROP NOT NULL;
ALTER TABLE feeds ADD COLUMN device text UNIQUE CHECK (device <> '');
ALTER TABLE feeds ADD CONSTRAINT feeds_url_or_device CHECK (num_nonnulls(url, device) = 1);

COMMENT ON COLUMN feeds.device IS 'Feed d''entrée audio : le périphérique de l''entrée (audio.inputs), à la place de l''adresse.';
