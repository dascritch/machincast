"""La règle de la normalisation du niveau (https://github.com/dascritch/machincast/issues/43).

Les réglages sont la section [plugins.loudness_normalization] de machincast.toml :

- target : la sonie visée, en LUFS, −23 par défaut (EBU R128) ;
- ceiling : le plafond de crête, en dBFS, −1 par défaut : la crête d'un sonore, gain compris, ne le dépasse jamais.

Le gain d'un sonore est le gain automatique, la cible moins sa sonie intégrée mesurée par l'audit complet
(https://github.com/dascritch/machincast/issues/642), plus son ajustement manuel, rangé dans sa colonne properties ;
il est borné pour que sa crête mesurée, gain compris, reste sous le plafond. Sans sonie mesurée, seul l'ajustement
manuel compte ; sans crête mesurée, rien ne le borne.
"""

from dataclasses import dataclass
from typing import Any

from machincast_loudness_normalization.texts import t

KEY = "loudness_normalization"
"""La clé du plugin, dans la colonne properties des sonores : {"loudness_normalization": {"gain": 2.5}}."""
MEASURE = "loudness"
"""La clé de la mesure du cœur, dans la colonne properties des sonores."""
LOWEST_TARGET = -40.0
HIGHEST_TARGET = -5.0
LOWEST_CEILING = -12.0
HIGHEST_CEILING = 0.0
MANUAL = 20.0
"""L'ajustement manuel le plus fort, en dB, dans un sens ou dans l'autre."""


@dataclass(frozen=True)
class Settings:
	target: float = -23.0
	ceiling: float = -1.0


@dataclass
class Current:
	"""Les réglages en vigueur dans le binaire, ou None s'ils sont refusés : dans Machin interface, la fenêtre du
	plugin les remplace à l'enregistrement ; Machin player et Machin indexer les relisent à leur démarrage."""

	settings: Settings | None = None


@dataclass(frozen=True)
class Measure:
	integrated: float | None = None
	peak: float | None = None


def _number(value: object) -> float | None:
	if (isinstance(value, bool)) or (not isinstance(value, (int, float))):
		return None
	return float(value)


def read_settings(section: dict[str, Any]) -> Settings | str:
	"""Les réglages de la section du plugin, ou pourquoi ils sont refusés."""
	defaults = Settings()
	target = _number(section.get("target", defaults.target))
	if (target is None) or (target < LOWEST_TARGET) or (target > HIGHEST_TARGET):
		return t("target is a loudness in LUFS, from -40 to -5")
	ceiling = _number(section.get("ceiling", defaults.ceiling))
	if (ceiling is None) or (ceiling < LOWEST_CEILING) or (ceiling > HIGHEST_CEILING):
		return t("ceiling is a peak in dBFS, from -12 to 0")
	return Settings(target, ceiling)


def as_section(settings: Settings) -> dict[str, Any]:
	return {"target": settings.target, "ceiling": settings.ceiling}


def measure(properties: dict[str, Any]) -> Measure:
	"""La mesure de l'audit complet, dans les properties du sonore."""
	found = properties.get(MEASURE)
	if not isinstance(found, dict):
		return Measure()
	return Measure(_number(found.get("integrated")), _number(found.get("peak")))


def manual(properties: dict[str, Any]) -> float:
	"""L'ajustement manuel du sonore, en dB ; 0 sans ajustement."""
	found = properties.get(KEY)
	if not isinstance(found, dict):
		return 0.0
	return (_number(found.get("gain"))) or (0.0)


def automatic(settings: Settings, measured: Measure) -> float:
	"""Le gain qui porte la sonie mesurée à la cible ; 0 sans sonie mesurée."""
	if measured.integrated is None:
		return 0.0
	return settings.target - measured.integrated


def headroom(settings: Settings, measured: Measure) -> float | None:
	"""Le plus fort ajustement manuel qui garde la crête sous le plafond ; None sans crête mesurée."""
	if measured.peak is None:
		return None
	return settings.ceiling - measured.peak - automatic(settings, measured)


def applied(settings: Settings, measured: Measure, adjustment: float) -> float:
	"""Le gain du sonore, en dB : automatique plus manuel, borné par le plafond de crête."""
	gain = automatic(settings, measured) + adjustment
	if measured.peak is not None:
		gain = min(gain, settings.ceiling - measured.peak)
	return round(gain, 1)


def tenth_below(value: float) -> float:
	"""Au dixième, sans dépasser la valeur : un ajustement qui garde la crête sous le plafond."""
	tenths = int(value * 10)
	if tenths > value * 10:
		tenths -= 1
	return tenths / 10
