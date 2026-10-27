"""MachinCast : système automatisé de diffusion sonore pour radio.

Les flux HTTP se lisent en HTTP/1.1 (https://github.com/dascritch/machincast/issues/278) : en HTTP/2, libsoup 3, par
qui GStreamer lit les streams, ne remonte pas l'expiration du délai d'une connexion qui ne donne plus rien
(https://gitlab.gnome.org/GNOME/libsoup/-/issues/256, https://gitlab.gnome.org/GNOME/libsoup/-/issues/367). Un stream
servi en HTTP/2 qui tombait laissait l'antenne en silence, sans erreur. La variable SOUP_FORCE_HTTP1 est posée ici,
avant toute session HTTP, pour tous les programmes de MachinCast. libsoup force HTTP/1.1 dès qu'elle existe, quelle
que soit sa valeur : posée par l'environnement, elle est gardée, à même effet.
"""

import os
from importlib.metadata import PackageNotFoundError, version

os.environ.setdefault("SOUP_FORCE_HTTP1", "1")

try:
	__version__ = version("machincast")
except PackageNotFoundError:  # exécution depuis les sources sans installation
	__version__ = "0.0.0"
