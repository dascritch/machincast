-- Les banques dans l'ordre ascendant du tableau de leurs sonores, du dernier au premier
-- (https://github.com/dascritch/machincast/issues/535) : comme le mode séquentiel, l'ordre descendant du tableau,
-- mais en remontant les positions.

ALTER TYPE bank_mode ADD VALUE 'sequential_ascending';
