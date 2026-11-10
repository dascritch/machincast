# language: fr
Fonctionnalité: Le service de diffusion lit les sonores, sous son propre compte
	En tant qu'administrateur du poste de l'antenne,
	je veux que le service de diffusion puisse lire les banques et les fichiers ajoutés, et savoir quand il ne le peut pas,
	afin qu'aucun sonore ne manque à l'antenne parce que son répertoire est privé.

	https://github.com/dascritch/machincast/issues/381. Le service tourne sous son propre compte, machincast
	(machincast.access) ; les scénarios prennent un autre compte, sans rien sur le poste, par MACHINCAST_SERVICE_ACCOUNT.
	Les droits se calculent comme le noyau : propriétaire, groupe, autres, ACL POSIX et leur masque. La lecture se donne
	par des ACL (setfacl), sans changer le propriétaire, le mode, ni le contenu d'aucun fichier
	(https://github.com/dascritch/machincast/issues/96).

	Contexte:
		Étant donné le compte du service « nobody »

	Plan du scénario: Le service lit ce que les droits du poste lui laissent lire
		Étant donné le répertoire « …/banque » en mode <répertoire>
		Et le fichier « …/banque/a.flac » en mode <fichier>
		Et <acl>
		Alors le service <lit> « …/banque/a.flac »

		Exemples:
			| répertoire | fichier | acl                                                       | lit       |
			| 0755       | 0644    | aucune ACL                                                | lit       |
			| 0755       | 0600    | aucune ACL                                                | ne lit pas |
			| 0700       | 0644    | aucune ACL                                                | ne lit pas |
			| 0755       | 0600    | l'ACL « u:nobody:r » sur « …/banque/a.flac »              | lit       |
			| 0755       | 0600    | l'ACL « u:nobody:r,m::--- » sur « …/banque/a.flac »         | ne lit pas |
			| 0700       | 0644    | l'ACL « u:nobody:x » sur « …/banque »                     | lit       |
			| 0755       | 0640    | l'ACL « g:nogroup:r » sur « …/banque/a.flac »             | lit       |

	Scénario: La lecture donnée traverse les parents, lit tout le répertoire, et les fichiers qui s'y ajouteront
		Étant donné le répertoire « …/maison » en mode 0700
		Et le répertoire « …/maison/banque » en mode 0700
		Et le fichier « …/maison/banque/a.flac » en mode 0600
		Et le répertoire « …/maison/banque/live » en mode 0700
		Et le fichier « …/maison/banque/live/b.flac » en mode 0600
		Quand la lecture de « …/maison/banque » est donnée au service
		Alors le service lit tout « …/maison/banque »
		Et le service traverse « …/maison » sans le lire
		Et les modes, les dates et le contenu des fichiers sont inchangés
		Quand le fichier « …/maison/banque/c.flac » s'ajoute, en mode 0640
		Alors le service lit « …/maison/banque/c.flac »

	Scénario: Un répertoire parent d'un autre compte est signalé, avec la commande d'un administrateur
		Hors des arborescences sensibles : le scénario se fait passer pour un autre compte que le propriétaire.

		Étant donné le répertoire « …/partage » en mode 0700
		Et le fichier « …/partage/a.flac » en mode 0644
		Et un compte qui n'est pas le propriétaire de « …/partage »
		Quand la lecture de « …/partage/a.flac » est demandée pour le service
		Alors la lecture n'est pas donnée, et le problème dit « sudo setfacl --modify=u:nobody:x »
		Et setfacl n'a été lancé que pour « …/partage/a.flac »

	Scénario: Machin grant-read donne la lecture des chemins donnés
		Étant donné le répertoire « …/banque » en mode 0700
		Et le fichier « …/banque/a.flac » en mode 0600
		Quand je lance « Machin grant-read » sur « …/banque »
		Alors la commande se termine avec le code 0
		Et le service lit tout « …/banque »

	Scénario: Machin grant-read, sans service installé, le dit
		Étant donné le compte du service « machincast-absent-des-tests »
		Quand je lance « Machin grant-read » sur « …/banque »
		Alors la commande se termine avec le code 1
		Et sa sortie d'erreur mentionne « pas de compte machincast-absent-des-tests : le service de diffusion n'est pas installé »

	Scénario: Ajouter des fichiers que le service ne lit pas propose de les lui faire lire
		Étant donné le répertoire « …/banque » en mode 0700
		Et le fichier « …/banque/a.flac » en mode 0600
		Quand l'interface ajoute « …/banque/a.flac », et que j'accepte de les faire lire au service
		Alors l'interface a demandé si le service peut lire « …/banque/a.flac »
		Et elle annonce « Le service de diffusion peut maintenant les lire. »
		Et le service lit « …/banque/a.flac »

	Scénario: Ajouter des fichiers que le service lit déjà ne demande rien
		Étant donné le répertoire « …/banque » en mode 0755
		Et le fichier « …/banque/a.flac » en mode 0644
		Quand l'interface ajoute « …/banque/a.flac », et que j'accepte de les faire lire au service
		Alors l'interface n'a rien demandé

	Plan du scénario: Les arborescences sensibles, où MachinCast ne change jamais de droits
		Alors « <chemin> » est dans le répertoire personnel <personnel>, et dans l'arborescence sensible <sensible>

		Exemples:
			| chemin                    | personnel          | sensible           |
			| /home/radio/sons/a.flac   | « /home/radio »    | « /home/radio »    |
			| /root/sons                | « /root »          | « /root »          |
			| /home/machincast/jingles  | aucun              | « /home »          |
			| /etc/machincast           | aucun              | « /etc »           |
			| /media/disque/sons        | aucun              | « /media »         |
			| /mnt/partage              | aucun              | « /mnt »           |
			| /usr/share/sounds         | aucun              | « /usr »           |
			| /                         | aucun              | « / »              |
			| /data/sons                | aucun              | aucune             |

	Scénario: Un lien vers un répertoire personnel y mène
		Étant donné le répertoire personnel « …/maison »
		Et le lien « …/sons » vers « …/maison »
		Alors « …/sons » est dans un répertoire personnel

	Scénario: Machin grant-read refuse de toucher aux droits d'une arborescence sensible, et n'y change rien
		Étant donné le répertoire personnel « …/maison »
		Et le répertoire « …/maison » en mode 0700
		Et le fichier « …/maison/a.flac » en mode 0600
		Quand la lecture de « …/maison/a.flac » est demandée pour le service
		Alors la lecture n'est pas donnée, et le problème dit « refusé »
		Et setfacl n'a pas été lancé

	Scénario: Machin grant-read part en échec dans un répertoire personnel
		Étant donné le répertoire personnel « …/maison »
		Et le répertoire « …/maison » en mode 0700
		Et le fichier « …/maison/a.flac » en mode 0600
		Quand je lance « Machin grant-read » sur « …/maison/a.flac »
		Alors la commande se termine avec le code 1
		Et sa sortie d'erreur mentionne « où MachinCast ne change jamais aucun droit »

	Scénario: L'interface du service refuse un sonore d'un répertoire personnel
		Étant donné le répertoire personnel « …/maison »
		Et le répertoire « …/maison » en mode 0755
		Et le fichier « …/maison/a.flac » en mode 0644
		Quand l'interface ajoute « …/maison/a.flac », et que j'accepte de les faire lire au service
		Alors l'interface n'a rien demandé, et refuse « …/maison/a.flac »
		Et elle annonce, entre autres, « dans un répertoire personnel, que le service de diffusion ne lit jamais »

	Scénario: L'interface du service accepte un sonore d'une arborescence sensible qu'il lit déjà
		Étant donné le fichier « /usr/bin/env » lisible par tous
		Quand l'interface ajoute « /usr/bin/env », et que j'accepte de les faire lire au service
		Alors l'interface n'a rien demandé, et accepte « /usr/bin/env »
