"""Un son continu sur une sortie PipeWire, dans un processus à part (https://github.com/dascritch/machincast/issues/384).

Les scénarios du verrou des sorties (tests/test_locked_output.py) le lancent avec l'environnement de leur PipeWire à
part : sur un poste qui a son propre PipeWire, un pipewiresink créé dans le processus des tests rejoignait celui du
poste, que le processus avait déjà joint, et jamais celui du scénario. Le processus écrit « prêt » une fois le
pipeline lancé, puis « erreur : … » à toute erreur, et s'arrête à la fermeture de son entrée.

	python -m tests.pipewire_player antenne      # la sortie de l'antenne, verrouillée sur le périphérique « antenne »
	python -m tests.pipewire_player sans-verrou  # une sortie sans verrou, sur le même périphérique
	python -m tests.pipewire_player factice      # l'antenne factice, sur sa carte virtuelle (#400)
"""

import contextlib
import select
import sys

from machincast import audio
from machincast.configuration import DUMMY, Audio
from machincast.player import virtual_card

DUMMY_ON_AIR = Audio(output="pipewire", device=DUMMY, preview="casque")


def output(kind: str) -> audio.Gst.Element:
	if kind == "antenne":
		return audio.create_output("pipewire", "antenne", presentation=audio.ON_AIR)
	element = audio.Gst.ElementFactory.make("pipewiresink", None)
	assert element is not None
	element.set_property("target-object", "antenne")
	audio.present(element, audio.Presentation("Sans verrou", "Antenne"))
	return element


def main(kind: str) -> int:
	audio.Gst.init(None)
	with contextlib.ExitStack() as stack:
		if kind == "factice":
			played = stack.enter_context(virtual_card.on_air(DUMMY_ON_AIR))
			return play(audio.create_output(*played.on_air(), presentation=audio.ON_AIR))
		return play(output(kind))


def play(sink: audio.Gst.Element) -> int:
	"""La source n'est pas en direct, comme les sonores de MachinCast : un pipeline à source en direct, sur un
	pipewiresink synchronisé, ne s'arrête plus avec le PipeWire à part."""
	audio.Gst.init(None)
	pipeline = audio.Gst.Pipeline.new(None)
	source = audio.Gst.ElementFactory.make("audiotestsrc", None)
	conversion = audio.Gst.ElementFactory.make("audioconvert", None)
	assert (source is not None) and (conversion is not None)
	for item in (source, conversion, sink):
		pipeline.add(item)
	source.link(conversion)
	conversion.link(sink)
	if pipeline.set_state(audio.Gst.State.PLAYING) == audio.Gst.StateChangeReturn.FAILURE:
		print("erreur : pipeline non lancé", flush=True)
		return 1
	print("prêt", flush=True)
	bus = pipeline.get_bus()
	while True:
		readable, _writable, _exceptional = select.select([sys.stdin], [], [], 0.1)
		if (readable) and (sys.stdin.read(1) == ""):
			break
		message = bus.pop_filtered(audio.Gst.MessageType.ERROR)
		if message is not None:
			error, _debug = message.parse_error()
			print(f"erreur : {error.message}", flush=True)
	pipeline.set_state(audio.Gst.State.NULL)
	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv[1]))
