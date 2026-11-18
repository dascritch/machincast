# language: fr
Fonctionnalité: Les cartes son du poste d'antenne ne s'endorment jamais
	En tant que technicien radio,
	je veux que les cartes son du poste d'antenne ne passent jamais en économie d'énergie,
	afin que l'antenne ne se coupe pas, ni ne claque, au réveil d'une carte.

	https://github.com/dascritch/machincast/issues/499. Deux réglages du système : l'option power_save=0 du module
	snd_hda_intel, les cartes son intégrées, dans /etc/modprobe.d ; et une règle udev qui laisse éveillés les
	périphériques USB, cartes son USB comprises, dans /etc/udev/rules.d. python -m machincast.power_save enable les
	installe et les applique aussitôt, disable les retire ; install.sh --service les installe avec le service, et
	--remove-service les retire. Sans service, en essai, le menu « Maintenance » les active et les désactive, avec
	l'authentification d'un administrateur (pkexec). Le scénario travaille dans une racine à part (--root), où
	/sys/module/snd_hda_intel/parameters/power_save est un fichier ; udevadm et pkexec y sont des scripts, en tête du
	PATH, qui notent leurs arguments ; pkexec lance ensuite la commande, sans autre droit.

	Contexte:
		Étant donné l'horloge de l'interface au « 2026-11-18 10:00:00 »

	# ─── Les réglages ──────────────────────────────────────────

	Scénario: Activer installe les deux réglages, et les applique aussitôt
		Étant donné snd_hda_intel chargé, en économie d'énergie après 1 seconde
		Quand je lance « python -m machincast.power_save enable » dans la racine du scénario
		Alors la commande se termine avec le code 0
		Et « /etc/modprobe.d/machincast.conf » contient la ligne « options snd_hda_intel power_save=0 »
		Et « /etc/udev/rules.d/50-machincast-usb.rules » contient la ligne « ACTION=="add|change", SUBSYSTEM=="usb", TEST=="power/control", ATTR{power/control}="on" »
		Et l'économie d'énergie de snd_hda_intel est à « 0 »
		Et udevadm a été lancé avec, dans l'ordre :
			| arguments                                  |
			| control --reload                           |
			| trigger --subsystem-match=usb --action=change |
		Et la commande a dit « cartes son toujours éveillées »

	Scénario: Sans snd_hda_intel chargé, son réglage vaudra à son chargement
		Quand je lance « python -m machincast.power_save enable » dans la racine du scénario
		Alors la commande se termine avec le code 0
		Et « /etc/modprobe.d/machincast.conf » contient la ligne « options snd_hda_intel power_save=0 »
		Et la commande a dit « snd_hda_intel n'est pas chargé : son réglage vaudra à son chargement »

	Scénario: Désactiver retire les deux réglages ; l'économie d'énergie revient au redémarrage
		Étant donné snd_hda_intel chargé, en économie d'énergie après 1 seconde
		Et les cartes son tenues éveillées dans la racine du scénario
		Quand je lance « python -m machincast.power_save disable » dans la racine du scénario
		Alors la commande se termine avec le code 0
		Et « /etc/modprobe.d/machincast.conf » n'existe plus
		Et « /etc/udev/rules.d/50-machincast-usb.rules » n'existe plus
		Et la commande a dit « réglages retirés : l'économie d'énergie des cartes son revient au prochain redémarrage »

	Scénario: Un réglage impossible à écrire est signalé
		Étant donné « /etc/modprobe.d », un fichier et non un répertoire, dans la racine du scénario
		Quand je lance « python -m machincast.power_save enable » dans la racine du scénario
		Alors la commande se termine avec le code 1
		Et la commande a dit un message qui commence par « cartes son non réglées : »

	Scénario: machincast.installation rédige les mêmes réglages, pour install.sh
		Alors « python -m machincast.installation power-save » écrit la ligne « options snd_hda_intel power_save=0 »
		Et « python -m machincast.installation usb-power » écrit la ligne « ACTION=="add|change", SUBSYSTEM=="usb", TEST=="power/control", ATTR{power/control}="on" »

	Scénario: install.sh, en installant le service, applique les réglages ; en le retirant, recharge udev
		Alors install.sh, en installant le service, lance « machincast.power_save wake » après les deux réglages
		Et install.sh, en retirant le service, recharge les règles de udev

	# ─── Le menu « Maintenance », sans service ─────────────────

	Scénario: Sans service, « Cartes son toujours éveillées » les active, puis les désactive, avec un administrateur
		Étant donné la racine du scénario pour les réglages des cartes son
		Quand la fenêtre de l'interface s'ouvre
		Alors l'entrée « Cartes son toujours éveillées » du menu « Maintenance » est active, décochée
		Quand je choisis « Cartes son toujours éveillées » dans le menu « Maintenance »
		Alors la barre d'état annonce bientôt « Cartes son toujours éveillées : elles ne passent plus en économie d'énergie. »
		Et pkexec a lancé « python -m machincast.power_save enable »
		Et l'entrée « Cartes son toujours éveillées » du menu « Maintenance » est active, cochée
		Quand je choisis « Cartes son toujours éveillées » dans le menu « Maintenance »
		Alors la barre d'état annonce bientôt « Cartes son de nouveau en économie d'énergie, au prochain redémarrage. »
		Et l'entrée « Cartes son toujours éveillées » du menu « Maintenance » est active, décochée

	Scénario: Une authentification refusée ne change rien, et le dit
		Étant donné la racine du scénario pour les réglages des cartes son
		Et pkexec qui refuse l'authentification
		Quand la fenêtre de l'interface s'ouvre
		Et je choisis « Cartes son toujours éveillées » dans le menu « Maintenance »
		Alors la barre d'état annonce bientôt « Cartes son non réglées : authentification refusée. »
		Et l'entrée « Cartes son toujours éveillées » du menu « Maintenance » est active, décochée

	Scénario: Avec le service de diffusion, l'entrée est inactive : install.sh --service tient les réglages
		Étant donné la racine du scénario pour les réglages des cartes son
		Et les cartes son tenues éveillées dans la racine du scénario
		Et le compte du service « root »
		Quand la fenêtre de l'interface s'ouvre
		Alors l'entrée « Cartes son toujours éveillées » du menu « Maintenance » est inactive, cochée, avec l'infobulle « Réglé par install.sh --service, avec le service de diffusion. »
