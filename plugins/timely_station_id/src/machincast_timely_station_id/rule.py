"""La règle du station ID régulier (https://github.com/dascritch/machincast/issues/460).

Les réglages sont la section [plugins.timely_station_id] de machincast.toml :

- bank : le nom interne de la banque des station ID à jouer ;
- watched : d'autres banques dont un passage compte comme un station ID, par exemple un jingle saisonnier qui dit le
  nom de la station ;
- minimum et maximum : en minutes, l'écart voulu entre deux station ID ;
- placement : « before », le station ID passe avant le morceau qui ferait dépasser le maximum, au plus tôt après le
  minimum ; « after », il passe au premier choix après le maximum, sans couper ni avancer aucun morceau.

Sans station ID connu, le premier passe aussitôt. Un morceau plus long que le maximum passe juste après un station ID :
rien ne le coupe.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from machincast_timely_station_id.texts import t

BEFORE = "before"
AFTER = "after"
PLACEMENTS = (BEFORE, AFTER)


@dataclass(frozen=True)
class Settings:
	bank: str
	watched: tuple[str, ...] = ()
	minimum: timedelta = timedelta(minutes=12)
	maximum: timedelta = timedelta(minutes=18)
	placement: str = BEFORE

	def banks(self) -> tuple[str, ...]:
		"""La banque jouée, puis les autres identifiants de la station."""
		return (self.bank, *self.watched)


def _minutes(value: object) -> timedelta | None:
	if (isinstance(value, bool)) or (not isinstance(value, (int, float))) or (value <= 0):
		return None
	return timedelta(minutes=value)


def read_settings(section: dict[str, Any]) -> Settings | str:
	"""Les réglages de la section du plugin, ou pourquoi ils sont refusés."""
	bank = section.get("bank")
	if (not isinstance(bank, str)) or (bank.strip() == ""):
		return t('the bank of the station IDs is missing: bank = "…"')
	watched = section.get("watched", [])
	if not isinstance(watched, list):
		return t("watched is a list of names of banks")
	names = []
	for name in watched:
		if not isinstance(name, str):
			return t("watched is a list of names of banks")
		names.append(name.strip())
	defaults = Settings(bank)
	minimum = _minutes(section.get("minimum", defaults.minimum.total_seconds() / 60))
	maximum = _minutes(section.get("maximum", defaults.maximum.total_seconds() / 60))
	if (minimum is None) or (maximum is None) or (minimum > maximum):
		return t("minimum and maximum are minutes, the minimum not above the maximum")
	placement = section.get("placement", BEFORE)
	if placement not in PLACEMENTS:
		return t("placement is “before” or “after”")
	return Settings(bank.strip(), tuple(names), minimum, maximum, str(placement))


def due(settings: Settings, elapsed: timedelta | None, duration: timedelta | None) -> bool:
	"""Un station ID passe-t-il avant le candidat : elapsed depuis le dernier, None sans station ID connu ; duration,
	celle du candidat, None pour un stream."""
	if (elapsed is None) or (elapsed >= settings.maximum):
		return True
	if (settings.placement == AFTER) or (duration is None) or (elapsed < settings.minimum):
		return False
	return elapsed + duration > settings.maximum


@dataclass
class Current:
	"""Les réglages en vigueur dans le binaire, ou None s'ils sont refusés : la fenêtre du plugin les remplace à
	l'enregistrement, pour la simulation et la fiche ; Machin player les relit à son démarrage."""

	settings: Settings | None = None


def as_section(settings: Settings) -> dict[str, Any]:
	"""La section [plugins.timely_station_id] des réglages."""
	section: dict[str, Any] = {"bank": settings.bank}
	if settings.watched != ():
		section["watched"] = list(settings.watched)
	section["minimum"] = _number(settings.minimum)
	section["maximum"] = _number(settings.maximum)
	section["placement"] = settings.placement
	return section


def _number(duration: timedelta) -> int | float:
	"""Des minutes entières sans décimale."""
	minutes = duration.total_seconds() / 60
	if minutes == int(minutes):
		return int(minutes)
	return minutes
