"""La pré-écoute de l'antenne, dans un processus à part (https://github.com/dascritch/machincast/issues/381).

Il se lance avec l'environnement du PipeWire à part d'une session, et MACHINCAST_SERVICE_RUNTIME vers le répertoire
d'exécution d'un autre PipeWire à part, celui du service : le lecteur de la pré-écoute de l'interface
(machincast.interface.preview.Player) y écoute l'antenne, et la joue sur la pré-écoute de la session. Le processus
écrit « prêt » une fois la lecture lancée, ou « erreur : … », et s'arrête à la fermeture de son entrée.

	python -m tests.pipewire_on_air_preview antenne casque
"""

import select
import sys

from machincast.configuration import Audio
from machincast.interface.preview import Player, Source


def main(on_air: str, preview: str) -> int:
	player = Player("pipewire", preview)
	player.load(Source("antenne", "antenne", True, None, Audio(output="pipewire", device=on_air, preview=preview)))
	player.read()
	if player.error is not None:
		print(f"erreur : {player.error}", flush=True)
		return 1
	print("prêt", flush=True)
	while True:
		readable, _writable, _exceptional = select.select([sys.stdin], [], [], 0.1)
		if (readable) and (sys.stdin.read(1) == ""):
			break
	player.halt()
	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv[1], sys.argv[2]))
