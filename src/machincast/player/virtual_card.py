"""La carte virtuelle de l'antenne factice (https://github.com/dascritch/machincast/issues/400).

Sur l'entrée « sortie factice » de l'antenne (audio.device = "dummy") d'une sortie PipeWire ou PulseAudio, Machin
player crée, le temps de sa diffusion, une carte virtuelle de PipeWire, « MachinCast antenne factice »
(support.null-audio-sink, node.name machincast_antenne_factice), et y joue l'antenne : l'interface en écoute le port de
monitoring, pour le VU-mètre et la pré-écoute de l'antenne, comme celui d'une vraie carte. Sous PulseAudio, c'est
pipewire-pulse qui la montre, comme une carte de PipeWire.

La carte est créée par un pw-cli, dont elle dépend (object.linger=false) : elle disparaît avec lui. pw-cli s'arrête à
la fin de la diffusion, et avec Machin player, même tué (PR_SET_PDEATHSIG). Sans pw-cli, ou sans PipeWire joignable,
l'antenne factice ne joue nulle part, comme avant, et le log le dit.
"""

import contextlib
import ctypes
import dataclasses
import logging
import shutil
import signal
import subprocess
import time
from collections.abc import Iterator, Mapping

from machincast.configuration import VIRTUAL_CARD, VIRTUAL_CARD_DESCRIPTION, Audio
from machincast.i18n import _

log = logging.getLogger("machincast.player")

PW_CLI = "pw-cli"
CREATION_ATTEMPTS = 50
"""Fois où pw-cli cherche la carte créée, toutes les CREATION_STEP secondes : PipeWire a environ 5 secondes pour la
montrer."""
CREATION_STEP = 0.1
QUERY_DELAY = 5.0
"""Secondes qu'a une commande pw-cli pour répondre."""
PR_SET_PDEATHSIG = 1
NODE = (
	"create-node adapter {{ factory.name=support.null-audio-sink node.name={name} "
	'node.description="{description}" media.class=Audio/Sink audio.position=[ FL FR ] object.linger=false }}\n'
)


class Unavailable(Exception):
	"""La carte virtuelle n'a pas pu être créée."""


def _die_with_parent() -> None:
	"""Dans pw-cli, avant son lancement : il reçoit SIGTERM quand Machin player s'arrête, même tué."""
	libc = ctypes.CDLL(None, use_errno=True)
	libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM)


def _exists(program: str, environment: Mapping[str, str] | None) -> bool:
	"""PipeWire a un nœud de ce nom."""
	try:
		result = subprocess.run(
			[program, "ls", "Node"],
			capture_output=True,
			text=True,
			timeout=QUERY_DELAY,
			stdin=subprocess.DEVNULL,
			env=environment,
		)
	except (OSError, subprocess.SubprocessError):
		return False
	return f'node.name = "{VIRTUAL_CARD}"' in result.stdout


def _stop(process: subprocess.Popen[str]) -> None:
	process.terminate()
	try:
		process.wait(timeout=QUERY_DELAY)
	except subprocess.TimeoutExpired:
		process.kill()
		process.wait()


def create(environment: Mapping[str, str] | None = None) -> subprocess.Popen[str]:
	"""Crée la carte virtuelle ; elle vit tant que le pw-cli rendu tourne. Lève Unavailable si elle n'apparaît pas."""
	program = shutil.which(PW_CLI)
	if program is None:
		raise Unavailable(_("pw-cli not found, install the pipewire-bin package"))
	try:
		process = subprocess.Popen(
			[program],
			stdin=subprocess.PIPE,
			stdout=subprocess.DEVNULL,
			stderr=subprocess.DEVNULL,
			text=True,
			env=environment,
			preexec_fn=_die_with_parent,
		)
	except OSError as error:
		raise Unavailable(str(error)) from None
	assert process.stdin is not None
	try:
		process.stdin.write(NODE.format(name=VIRTUAL_CARD, description=VIRTUAL_CARD_DESCRIPTION))
		process.stdin.flush()
	except OSError as error:
		_stop(process)
		raise Unavailable(str(error)) from None
	for _attempt in range(CREATION_ATTEMPTS):
		if process.poll() is not None:
			raise Unavailable(_("PipeWire unreachable"))
		if _exists(program, environment):
			return process
		time.sleep(CREATION_STEP)
	_stop(process)
	raise Unavailable(_("PipeWire unreachable"))


@contextlib.contextmanager
def on_air(audio: Audio, environment: Mapping[str, str] | None = None) -> Iterator[Audio]:
	"""La configuration audio où joue l'antenne, le temps de la diffusion : sur l'entrée « sortie factice » d'une
	sortie PipeWire ou PulseAudio, la carte virtuelle, créée pour l'occasion et retirée à la fin ; sinon, celle donnée,
	telle quelle."""
	if not audio.virtual_on_air():
		yield audio
		return
	try:
		process = create(environment)
	except Unavailable as error:
		log.warning(
			_("virtual card “{name}” not created ({reason}): the dummy output plays no sound").format(
				name=VIRTUAL_CARD_DESCRIPTION, reason=error
			)
		)
		yield audio
		return
	log.info(_("on air on the virtual card “{name}”").format(name=VIRTUAL_CARD_DESCRIPTION))
	try:
		yield dataclasses.replace(audio, device=VIRTUAL_CARD)
	finally:
		_stop(process)
