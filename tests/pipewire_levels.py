"""Le niveau le plus haut que relève le port de monitoring de l'antenne, dans un processus à part
(https://github.com/dascritch/machincast/issues/400).

Comme tests/pipewire_player.py, il se lance avec l'environnement d'un PipeWire à part : un pipewiresrc créé dans le
processus des tests rejoindrait le PipeWire du poste. Il écoute le port de l'antenne de la configuration donnée, comme
le VU-mètre de l'interface, pendant SECONDS secondes, puis écrit le plus haut niveau RMS relevé, en dB.

	python -m tests.pipewire_levels pipewire dummy   # l'antenne factice d'une sortie PipeWire
"""

import sys
import time

from machincast import audio
from machincast.configuration import Audio
from machincast.interface import monitor

SECONDS = 3.0


def main(output: str, device: str) -> int:
	audio.Gst.init(None)
	pipeline = audio.Gst.Pipeline.new(None)
	source = monitor.monitor_source(Audio(output=output, device=device, preview="casque"))  # type: ignore[arg-type]
	level = audio.Gst.ElementFactory.make("level", None)
	sink = audio.Gst.ElementFactory.make("fakesink", None)
	assert (level is not None) and (sink is not None)
	level.set_property("post-messages", True)
	for item in (source, level, sink):
		pipeline.add(item)
	source.link(level)
	level.link(sink)
	pipeline.set_state(audio.Gst.State.PLAYING)
	highest = -200.0
	bus = pipeline.get_bus()
	limit = time.monotonic() + SECONDS
	while time.monotonic() < limit:
		message = bus.timed_pop_filtered(100 * audio.Gst.MSECOND, audio.Gst.MessageType.ELEMENT)
		if message is not None:
			structure = message.get_structure()
			if (structure is not None) and (structure.get_name() == "level"):
				for value in structure.get_value("rms"):
					highest = max(highest, float(value))
	pipeline.set_state(audio.Gst.State.NULL)
	print(f"{highest:.1f}", flush=True)
	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv[1], sys.argv[2]))
