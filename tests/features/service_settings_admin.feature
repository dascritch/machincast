# language: fr
Fonctionnalité: Les paramètres du service se règlent avec le mot de passe d'un administrateur
	En tant que responsable de l'antenne,
	je veux qu'on ne puisse pas régler le service sans un administrateur, par exemple le niveau sonore de l'antenne,
	afin qu'une fausse manœuvre au studio ne change pas l'antenne.

	https://github.com/dascritch/machincast/issues/603, ticket enfant de
	https://github.com/dascritch/machincast/issues/596. Le service installé, ouvrir « Paramètres du service… » demande à
	polkit l'action org.machincast.service-settings, par pkcheck, qui fait demander par l'agent polkit le mot de passe
	d'un administrateur, le sien s'il l'est ; pkcheck est imité par un script qui note ses arguments, et répond oui ou
	non. Refusée ou annulée, la fenêtre s'ouvre en consultation.

	Contexte:
		Étant donné l'horloge de l'interface au « 2026-11-20 10:00:00 »
		Et les préférences du scénario notées, avec leur consultation

	Scénario: Le service installé, un administrateur autorise : la fenêtre des paramètres du service se règle
		Étant donné le service de diffusion est installé
		Et polkit, qui autorise l'action
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors polkit a vérifié l'action « org.machincast.service-settings » pour l'interface, en demandant l'authentification
		Et la fenêtre des paramètres du service s'est ouverte, modifiable

	Plan du scénario: Le service installé, sans administrateur, la fenêtre s'ouvre en consultation
		Étant donné le service de diffusion est installé
		Et polkit, <réponse>
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors la fenêtre des paramètres du service s'est ouverte, en consultation

		Exemples:
			| réponse                    |
			| qui refuse l'action        |
			| absent du poste            |

	Scénario: Sans le service installé, la fenêtre des paramètres du service se règle sans rien demander
		Étant donné le service de diffusion n'est pas installé
		Et polkit, qui refuse l'action
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Paramètres du service… » dans le menu « Fichier »
		Alors polkit n'a rien vérifié
		Et la fenêtre des paramètres du service s'est ouverte, modifiable

	Scénario: Les préférences de l'interface ne demandent jamais d'administrateur
		Étant donné le service de diffusion est installé
		Et polkit, qui refuse l'action
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Préférences de l'interface… » dans le menu « Fichier »
		Alors polkit n'a rien vérifié
		Et la fenêtre des préférences de l'interface s'est ouverte, modifiable

	Scénario: En consultation, chaque page se lit sans se régler, et la fenêtre ne s'enregistre pas
		Quand la fenêtre des paramètres du service s'ouvre en consultation
		Alors elle est titrée « Paramètres du service (consultation) »
		Et elle dit « Consultation seulement : un administrateur n'a pas autorisé à régler le service. »
		Et chacune de ses pages est en lecture seule, ses onglets toujours au choix
		Et elle n'a que le bouton « Fermer »
