"""La mesure du niveau d'un sonore, pendant le décodage de l'audit complet
(https://github.com/dascritch/machincast/issues/642, pour https://github.com/dascritch/machincast/issues/43).

Le son décodé est rééchantillonné à 48 kHz, en flottants : sa crête absolue est le plus grand échantillon, en valeur
absolue, en dBFS, la référence de la saturation. Puis il passe par la pondération K de la recommandation ITU-R BS.1770
(deux filtres audioiirfilter, aux coefficients de la recommandation à 48 kHz) : sa sonie intégrée EBU R128, en LUFS, est
calculée avec numpy sur des blocs de 400 ms qui se recouvrent de 75 %, sous la porte absolue de −70 LUFS, puis sous la
porte relative, 10 LU sous la sonie des blocs retenus. Un son qui n'atteint jamais la porte absolue, ou plus court
qu'un bloc, n'a pas de sonie intégrée ; un silence numérique n'a pas de crête.
"""

import math
from dataclasses import dataclass, field
from typing import Any

import gi
import numpy

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

RATE = 48000
"""La fréquence d'échantillonnage de la mesure : celle des coefficients de la pondération K."""
CAPS = f"audio/x-raw,format=F32LE,layout=interleaved,rate={RATE}"
SUB_BLOCK = RATE // 10
"""Une tranche de 100 ms : quatre font un bloc de 400 ms, et un bloc avance d'une tranche (75 % de recouvrement)."""
BLOCK = 4
ABSOLUTE_GATE = -70.0
RELATIVE_GATE = -10.0
OFFSET = -0.691
"""Le décalage de BS.1770, qui donne −3,01 LUFS à une sinusoïde de 997 Hz à 0 dBFS sur un seul canal."""
K_WEIGHTING = (
	# Le premier filtre, en plateau, imite l'effet acoustique de la tête ; le second, passe-haut, la courbe RLB.
	((1.53512485958697, -2.69169618940638, 1.19839281085285), (1.0, -1.69065929318241, 0.73248077421585)),
	((1.0, -2.0, 1.0), (1.0, -1.99004745483398, 0.99007225036621)),
)
"""Les coefficients b (numérateur) et a (dénominateur) de chaque filtre de la pondération K, à 48 kHz."""
SURROUND = 1.41
"""Le poids des canaux d'ambiance, au-delà des trois premiers ; celui du canal LFE d'un 5.1 est nul."""


@dataclass(frozen=True)
class Loudness:
	integrated: float | None
	"""La sonie intégrée EBU R128, en LUFS ; None pour un son trop court ou trop faible."""
	peak: float | None
	"""La crête absolue, en dBFS ; None pour un silence numérique."""

	def properties(self) -> dict[str, Any]:
		"""Ce qui est rangé dans la colonne properties du sonore, sous la clé « loudness », au dixième près."""
		return {"integrated": _tenth(self.integrated), "peak": _tenth(self.peak)}


def _tenth(value: float | None) -> float | None:
	if value is None:
		return None
	return round(value, 1)


def weights(channels: int) -> numpy.ndarray:
	"""Le poids de chaque canal : 1 pour les trois premiers, SURROUND au-delà ; nul pour le LFE d'un 5.1."""
	found = numpy.ones(channels)
	if channels > 3:
		found[3:] = SURROUND
	if channels == 6:
		found[3] = 0.0
	return found


@dataclass
class Meter:
	"""Ce que les sondes voient passer : la crête avant la pondération K, l'énergie de chaque tranche après."""

	peak: float = 0.0
	powers: list[float] = field(default_factory=list)
	"""La puissance pondérée de chaque tranche de 100 ms, les canaux sommés selon leur poids."""
	rest: numpy.ndarray | None = None
	"""Les échantillons pondérés qui n'emplissent pas encore une tranche."""

	def note_peak(self, samples: numpy.ndarray) -> None:
		if samples.size > 0:
			self.peak = max(self.peak, float(numpy.max(numpy.abs(samples))))

	def note_weighted(self, samples: numpy.ndarray) -> None:
		"""Des échantillons pondérés, par canal en colonnes."""
		if self.rest is not None:
			samples = numpy.concatenate((self.rest, samples))
		count = len(samples) // SUB_BLOCK
		if count > 0:
			slices = samples[: count * SUB_BLOCK].reshape(count, SUB_BLOCK, samples.shape[1]).astype(numpy.float64)
			means = numpy.mean(slices * slices, axis=1)
			self.powers.extend((means @ weights(samples.shape[1])).tolist())
		self.rest = samples[count * SUB_BLOCK :]

	def result(self) -> Loudness:
		return Loudness(integrated(self.powers), _decibels(self.peak))


def _decibels(peak: float) -> float | None:
	if peak <= 0.0:
		return None
	return 20 * math.log10(peak)


def _lufs(power: numpy.ndarray) -> numpy.ndarray:
	with numpy.errstate(divide="ignore"):
		return OFFSET + 10 * numpy.log10(power)


def integrated(powers: list[float]) -> float | None:
	"""La sonie intégrée, d'après la puissance pondérée de chaque tranche de 100 ms ; None sans bloc au-dessus de la
	porte absolue."""
	if len(powers) < BLOCK:
		return None
	slices = numpy.array(powers)
	blocks = numpy.convolve(slices, numpy.ones(BLOCK) / BLOCK, mode="valid")
	kept = blocks[_lufs(blocks) > ABSOLUTE_GATE]
	if kept.size == 0:
		return None
	threshold = float(_lufs(numpy.array([numpy.mean(kept)]))[0]) + RELATIVE_GATE
	kept = kept[_lufs(kept) > threshold]
	if kept.size == 0:
		return None
	return float(_lufs(numpy.array([numpy.mean(kept)]))[0])


def _samples(pad: Gst.Pad, buffer: Gst.Buffer) -> numpy.ndarray | None:
	"""Les échantillons du tampon, un canal par colonne ; None sans capacités connues."""
	capabilities = pad.get_current_caps()
	if (capabilities is None) or (capabilities.get_size() == 0):
		return None
	known, channels = capabilities.get_structure(0).get_int("channels")
	if (not known) or (channels <= 0):
		return None
	success, mapping = buffer.map(Gst.MapFlags.READ)
	if not success:
		return None
	try:
		data = numpy.frombuffer(bytes(mapping.data), dtype="<f4")
	finally:
		buffer.unmap(mapping)
	usable = len(data) - len(data) % channels
	return data[:usable].reshape(-1, channels)


def peak_probe(meter: Meter) -> Any:
	def probe(pad: Gst.Pad, info: Gst.PadProbeInfo) -> Gst.PadProbeReturn:
		buffer = info.get_buffer()
		if buffer is not None:
			samples = _samples(pad, buffer)
			if samples is not None:
				meter.note_peak(samples)
		return Gst.PadProbeReturn.OK

	return probe


def weighted_probe(meter: Meter) -> Any:
	def probe(pad: Gst.Pad, info: Gst.PadProbeInfo) -> Gst.PadProbeReturn:
		buffer = info.get_buffer()
		if buffer is not None:
			samples = _samples(pad, buffer)
			if samples is not None:
				meter.note_weighted(samples)
		return Gst.PadProbeReturn.OK

	return probe


def k_filters() -> list[Gst.Element] | None:
	"""Les deux filtres de la pondération K ; None si audioiirfilter manque."""
	found = []
	for numerator, denominator in K_WEIGHTING:
		element = Gst.ElementFactory.make("audioiirfilter", None)
		if element is None:
			return None
		element.set_property("b", list(numerator))
		element.set_property("a", list(denominator))
		found.append(element)
	return found
