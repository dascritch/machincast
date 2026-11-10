# language: fr
Fonctionnalité: L'interface joint l'antenne sur le PipeWire du service de diffusion
	En tant que programmateur, sur le poste dédié à l'antenne,
	je veux voir le VU-mètre de l'antenne, la pré-écouter et choisir sa carte son depuis ma session,
	afin de suivre la diffusion que fait le service, sous son propre compte, avec son propre PipeWire.

	https://github.com/dascritch/machincast/issues/381. Le service joue par son PipeWire, dont la socket est dans son
	répertoire d'exécution, /run/machincast (machincast.service.RUNTIME), au groupe machincast où est le compte de
	MachinCast ; la carte de l'antenne est cachée au PipeWire de la session. L'interface joint celui du service par sa
	socket (propriété fd des éléments PipeWire de GStreamer) : le VU-mètre, la pré-écoute de l'antenne, qu'un pipeline
	relaie vers la pré-écoute de la session, et la liste des cartes de l'antenne. La socket d'état y est aussi.

	Scénario: Sans service, la socket d'état est dans le répertoire d'exécution du compte
		Étant donné un poste sans service de diffusion
		Alors la socket d'état par défaut est « machincast/lecture.sock » du répertoire d'exécution du compte

	Scénario: Avec le service, la socket d'état est dans son répertoire, au groupe du service
		Étant donné le répertoire d'exécution du service, au groupe, en mode 2770
		Quand Machin player ouvre sa socket d'état par défaut
		Alors la socket d'état est « lecture.sock » du répertoire du service, en mode 0660
		Et le répertoire du service garde son mode 2770

	Scénario: Le VU-mètre écoute l'antenne sur le PipeWire du service, que la session ne voit pas
		Étant donné un PipeWire à part pour le service, avec la carte « antenne », où Machin player joue
		Quand le port de monitoring de l'antenne « antenne » est écouté depuis une session sans PipeWire
		Alors il relève un son au-dessus de -40 dB

	Scénario: La pré-écoute de l'antenne passe du PipeWire du service à celui de la session
		Étant donné un PipeWire à part pour le service, avec la carte « antenne », où Machin player joue
		Et un PipeWire à part pour la session, avec la carte « casque »
		Quand la pré-écoute de l'interface écoute l'antenne « antenne » sur « casque »
		Alors le flux de la pré-écoute joue sur « casque » dans le PipeWire de la session

	Scénario: La carte de l'antenne se choisit parmi celles du PipeWire du service
		Étant donné un PipeWire à part pour le service, avec la carte « antenne », où Machin player joue
		Quand les cartes de l'antenne sont listées depuis une session sans PipeWire
		Alors la liste a « antenne »

	Scénario: Le son de test de la carte de l'antenne joue sur le PipeWire du service
		Étant donné un PipeWire à part pour le service, avec la carte « antenne », où Machin player joue
		Quand le son de test de la carte de l'antenne « antenne » est lancé depuis une session sans PipeWire
		Alors le son de test joue sur « antenne » dans le PipeWire du service

	Scénario: Le niveau et la sourdine de la carte de l'antenne se règlent sur le PipeWire du service
		Étant donné un PipeWire à part pour le service, avec la carte « antenne », où Machin player joue
		Quand le niveau de la carte de l'antenne « antenne » est réglé à 40 %, sourdine mise
		Alors le PipeWire du service a la carte « antenne » à 40 %, en sourdine
		Quand la sourdine de la carte de l'antenne « antenne » est levée
		Alors le PipeWire du service a la carte « antenne » à 40 %, sans sourdine

	Scénario: La page Audio du service règle le niveau et la sourdine de la carte de l'antenne
		Étant donné un PipeWire à part pour le service, avec la carte « antenne », où Machin player joue
		Et le niveau de la carte de l'antenne « antenne » réglé à 70 %
		Quand la page Audio s'ouvre en mode service, l'antenne sur « antenne »
		Alors la page montre le niveau de l'antenne à 70 %, sans sourdine
		Quand je règle le niveau de l'antenne à 25 % et coche « Muet »
		Alors le PipeWire du service a la carte « antenne » à 25 %, en sourdine

	Scénario: Sans service, la page Audio ne montre pas le niveau de l'antenne
		Quand la page Audio s'ouvre sans service, l'antenne sur « antenne »
		Alors la page ne montre pas le niveau de l'antenne

	Scénario: Un compte qui ne joint pas le PipeWire du service le dit sur le VU-mètre
		Étant donné un service dont le PipeWire refuse la connexion
		Quand le port de monitoring de l'antenne « antenne » s'ouvre
		Alors il est indisponible : « le PipeWire du service de diffusion ne répond pas »

	Scénario: L'infobulle du VU-mètre nomme le PipeWire du service
		Étant donné un service dont le PipeWire refuse la connexion
		Alors le port de monitoring de l'antenne « antenne » se nomme « PipeWire du service de diffusion, antenne »
