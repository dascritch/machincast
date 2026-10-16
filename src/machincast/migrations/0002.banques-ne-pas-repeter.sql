-- Banque « ne pas répéter » (https://github.com/dascritch/machincast/issues/63, doc/spec.md § 3.1 et § 4.4) :
-- une banque marquée ne passe jamais deux fois de suite. Les banques existantes ne sont pas marquées.
-- depends: 0001.schema-initial

ALTER TABLE banques ADD COLUMN ne_pas_repeter boolean NOT NULL DEFAULT false;
