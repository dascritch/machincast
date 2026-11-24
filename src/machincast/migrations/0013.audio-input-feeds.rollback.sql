-- Un feed d'entrée audio redevient un feed d'adresse : son adresse est celle que jouent ses streams.
ALTER TABLE feeds DROP CONSTRAINT feeds_url_or_device;
UPDATE feeds SET url = 'input:' || device WHERE device IS NOT NULL;
ALTER TABLE feeds DROP COLUMN device;
ALTER TABLE feeds ALTER COLUMN url SET NOT NULL;
