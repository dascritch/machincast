# language: fr
@release
Fonctionnalité: Un flux servi en HTTP/2 qui gèle est vu tomber
	En tant que responsable d'antenne,
	je veux que MachinCast voie tomber un flux HTTP/2 qui ne donne plus rien,
	afin qu'un direct comme celui de France Inter ne laisse jamais de blanc à l'antenne.

	https://github.com/dascritch/machincast/issues/278 : en HTTP/2, libsoup 3, par qui GStreamer lit les streams, ne
	signale pas l'expiration du délai d'une connexion qui ne donne plus rien
	(https://gitlab.gnome.org/GNOME/libsoup/-/issues/256, https://gitlab.gnome.org/GNOME/libsoup/-/issues/367).
	MachinCast lit donc ses flux en HTTP/1.1 (SOUP_FORCE_HTTP1), et tient pour tombé un stream sans son pendant le délai
	de garde.

	Ces scénarios se lancent à part, avant chaque version, et après une mise à jour de GStreamer ou de libsoup :
	pytest -m release. Ils servent un flux AAC en local, chiffré, par hypercorn, en HTTP/2 ; le flux gèle au bout de
	3 secondes, sa connexion ouverte, comme un réseau coupé. Voir TROUBLESHOOTING.md.

	Contexte:
		Étant donné un serveur de flux HTTP/2 local, chiffré, dont le flux AAC gèle au bout de 3 secondes

	Scénario: Lu comme le lit MachinCast, en HTTP/1.1, le flux gelé est signalé par le lecteur
		Quand une voie de Machin lecture lit ce flux, en HTTP/1.1, jusqu'à 15 secondes après le gel
		Alors le serveur a servi le flux en HTTP/1.1
		Et la voie est en erreur au plus 15 secondes après le gel

	Scénario: En HTTP/2, le lecteur ne signale rien, mais la garde voit la voie gelée
		Si ce scénario échoue sur « la voie est toujours en cours », libsoup signale désormais le gel en HTTP/2 :
		SOUP_FORCE_HTTP1 peut alors être reconsidéré.

		Quand une voie de Machin lecture lit ce flux, en HTTP/2, jusqu'à 15 secondes après le gel
		Alors le serveur a servi le flux en HTTP/2
		Et la voie est toujours en cours, sans erreur
		Et la voie est gelée
