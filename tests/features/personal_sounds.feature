# language: fr
Fonctionnalité: Les sonores des répertoires personnels, à l'installation du service
	En tant qu'administrateur du poste de l'antenne,
	je veux qu'install.sh --service déplace hors de mon répertoire personnel, si je l'accepte, les sonores que la base y
	connaît, ou les retire de la base,
	afin que le service de diffusion n'ait jamais à lire un répertoire personnel, dont les droits ne changent jamais.

	https://github.com/dascritch/machincast/issues/381. Le déplacement, accepté à chaque fois, est la seule exception à
	https://github.com/dascritch/machincast/issues/96. Les scénarios simulent un répertoire personnel
	(MACHINCAST_PERSONAL_HOMES) et le répertoire d'accueil des sonores (MACHINCAST_WELCOME) dans leur répertoire
	temporaire, avec la base de test.

	Contexte:
		Étant donné le répertoire personnel « maison » et le répertoire d'accueil « accueil »
		Et la banque « Jingles », du répertoire « maison/jingles », avec le sonore « maison/jingles/a.flac »
		Et la banque « Ailleurs », du répertoire « studio/sons », avec le sonore « studio/sons/b.flac »
		Et le sonore ajouté « maison/telechargements/c.flac »

	Scénario: La base connaît des sonores dans un répertoire personnel
		Quand les sonores des répertoires personnels sont listés
		Alors la liste est « maison/jingles », « maison/telechargements/c.flac »

	Scénario: Les sonores se déplacent dans le répertoire d'accueil, et la base suit
		Quand les sonores des répertoires personnels sont déplacés
		Alors le fichier « accueil/jingles/a.flac » existe, et plus « maison/jingles/a.flac »
		Et le fichier « accueil/fichiers/c.flac » existe, et plus « maison/telechargements/c.flac »
		Et la banque « Jingles » a le répertoire « accueil/jingles »
		Et les sonores sont « accueil/fichiers/c.flac », « accueil/jingles/a.flac », « studio/sons/b.flac »
		Et le contenu des fichiers déplacés est inchangé

	Scénario: Un nom déjà pris dans le répertoire d'accueil reçoit un suffixe
		Étant donné le fichier « accueil/fichiers/c.flac » déjà présent
		Quand les sonores des répertoires personnels sont déplacés
		Alors le fichier « accueil/fichiers/c-2.flac » existe, et plus « maison/telechargements/c.flac »
		Et le fichier « accueil/fichiers/c.flac » est inchangé

	Scénario: Si la base refuse, les fichiers reviennent à leur place
		Étant donné une base qui refuse la mise à jour des emplacements
		Quand les sonores des répertoires personnels sont déplacés
		Alors le déplacement échoue
		Et le fichier « maison/jingles/a.flac » existe, et plus « accueil/jingles/a.flac »
		Et le fichier « maison/telechargements/c.flac » existe, et plus « accueil/fichiers/c.flac »

	Scénario: Les sonores se retirent de la base, sans qu'aucun fichier ne bouge
		Quand les sonores des répertoires personnels sont retirés de la base
		Alors les sonores sont « studio/sons/b.flac »
		Et la banque « Jingles » n'a plus de répertoire
		Et le fichier « maison/jingles/a.flac » existe, et plus « accueil/jingles/a.flac »
		Et le fichier « maison/telechargements/c.flac » existe, et plus « accueil/fichiers/c.flac »
