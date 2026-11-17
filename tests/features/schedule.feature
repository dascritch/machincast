# language: fr
Fonctionnalité: Tâches quotidiennes à l'heure réglée
	En tant que technicien radio,
	je veux que la purge de la base et l'audit complet des sonores passent chaque jour à une heure que je règle,
	afin qu'en cas de souci, quelqu'un soit au studio pour s'en apercevoir.

	https://github.com/dascritch/machincast/issues/455. Un minuteur systemd fixe, installé par install.sh --service, se
	déclenche tous les quarts d'heure ; il ne lance la tâche quotidienne (Machin purge, puis Machin indexer --full-audit)
	que si machincast.schedule la dit due : l'heure réglée (schedule.daily) de la dernière occurrence passée n'a pas
	encore été servie. L'heure se règle dans machincast.toml, sans droit d'administrateur ; une tâche manquée, poste
	éteint à l'heure, passe au quart d'heure qui suit son démarrage. Le dernier passage se note dans le répertoire d'état
	de l'unité (STATE_DIRECTORY).

	Plan du scénario: La tâche quotidienne est due une fois par jour, à partir de l'heure réglée
		Étant donné les tâches quotidiennes réglées à « 10:00 »
		Et leur dernier passage <dernier>
		Alors le « <maintenant> », la tâche quotidienne <verdict>

		Exemples:
			| dernier                  | maintenant       | verdict       |
			| jamais                   | 2026-11-17 09:59 | est due       |
			| le « 2026-11-16 10:00 »  | 2026-11-17 09:59 | n'est pas due |
			| le « 2026-11-16 10:00 »  | 2026-11-17 10:00 | est due       |
			| le « 2026-11-17 10:00 »  | 2026-11-17 10:15 | n'est pas due |
			| le « 2026-11-17 10:00 »  | 2026-11-17 23:59 | n'est pas due |
			| le « 2026-11-15 10:00 »  | 2026-11-17 08:00 | est due       |
			| le « 2026-11-16 09:59 »  | 2026-11-16 18:00 | est due       |

	Scénario: Une heure changée vaut dès le jour même, sans repasser deux fois
		Étant donné les tâches quotidiennes réglées à « 14:00 »
		Et leur dernier passage le « 2026-11-17 10:00 »
		Alors le « 2026-11-17 11:00 », la tâche quotidienne n'est pas due
		Et le « 2026-11-17 14:00 », la tâche quotidienne est due

	Scénario: Le passage d'heure d'été ne fait ni sauter ni doubler la tâche
		Étant donné le poste à l'heure de Paris
		Et les tâches quotidiennes réglées à « 02:30 »
		Et leur dernier passage le « 2026-03-28 02:30 »
		Alors le « 2026-03-29 04:00 », la tâche quotidienne est due

	Scénario: La tâche quotidienne se réserve une seule fois : le premier lancement la prend, le suivant la trouve faite
		https://github.com/dascritch/machincast/issues/455 : la réserve se note avant la tâche, pour qu'une tâche en échec
		ne soit pas relancée tous les quarts d'heure ; son échec est dans le journal et le log de la base.
		Étant donné un répertoire d'état vide
		Et une configuration de test où les tâches quotidiennes passent à « 00:00 »
		Quand je lance « python -m machincast.schedule claim »
		Alors la réserve se termine par le code 0
		Et le répertoire d'état garde l'heure de ce passage
		Quand je lance « python -m machincast.schedule claim »
		Alors la réserve se termine par le code 1

	Scénario: Sans répertoire d'état, la réserve échoue, et le dit
		Étant donné une configuration de test où les tâches quotidiennes passent à « 00:00 »
		Quand je lance « python -m machincast.schedule claim » sans répertoire d'état
		Alors la réserve se termine par le code 2
		Et sa sortie d'erreur mentionne « STATE_DIRECTORY »
