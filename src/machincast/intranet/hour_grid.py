"""La semaine de la page /calendar en grille horaire, comme le calendrier de l'interface
(https://github.com/dascritch/machincast/issues/580, machincast.interface.calendar).

- Une colonne par jour, du lundi au dimanche, de 0 h à 24 h, les heures à gauche ; aujourd'hui en gras, et l'heure
  actuelle d'un trait rouge. La grille montre 12 heures dans sa hauteur, et défile ; le script (static/intranet.js)
  l'ouvre à 07:00 (FIRST_HOUR).
- Chaque occurrence est un bloc à ses heures, de la couleur de sa priorité : pleine où elle est à l'antenne, estompée
  où un autre événement la couvre, hachurée pour une session sautée. Ceux qui se chevauchent se placent côte à côte
  (machincast.shared.side_by_side, comme l'interface). Son infobulle dit son nom, sa priorité, ses heures et ce qui en
  joue.
- Une occurrence de 24 heures ou plus, dont le fil musical permanent, va dans la bande de la journée entière, sous le
  nom des jours ; elle y est pleine, de gauche à droite, à ses heures à l'antenne.
- Les blocs estompés gardent une teinte claire, opaque, et le texte des blocs reste sombre, en thème sombre aussi. Sur
  un écran étroit, les jours prennent leur nom court (short_title).

En SVG, sans script ni attribut style, que la politique de sécurité du contenu (default-src 'self') refuse : chaque
bloc est un <svg> imbriqué, placé en pourcentages, qui coupe ce qui le dépasse ; son texte est en HTML hCalendar, dans
un <foreignObject> : un `vevent` (`h-event`), son nom en `summary`, ses heures de ce jour en `dtstart` et `dtend`, sa
priorité en `category`.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from html import escape
from typing import Any

from machincast.i18n import _
from machincast.intranet.calendar import ONE_DAY, PRIORITIES, WEEK, day_title, end_hour, hour, midnight, remark
from machincast.shared.colours import BLACK, WHITE, mixed, readable_text
from machincast.shared.grid import DAY_NAMES, RANKS, Priority
from machincast.shared.side_by_side import columns

HOUR_HEIGHT = 48
"""Pixels d'une heure de la grille."""
FIRST_HOUR = 7
"""L'heure en haut de la grille à l'ouverture de la page, comme dans l'interface ; le script y fait défiler la grille."""
NAME_HEIGHT = 24
"""Pixels du nom des jours."""
LINE_HEIGHT = 22
"""Pixels d'un bloc de la bande de la journée entière."""
GAP = 4
MINUTES = 24 * 60
MASK = _("by another event")


@dataclass(frozen=True)
class Block:
	"""Une occurrence, sur un jour de la semaine."""

	ordinal: int
	"""Son rang dans le calendrier : deux occurrences aux mêmes heures font deux blocs."""
	day: date
	start: datetime
	end: datetime
	plays: tuple[tuple[datetime, datetime], ...]
	"""Ses moments à l'antenne, ce jour-là."""
	whole_day: bool
	"""Dans la bande de la journée entière."""
	entry: dict[str, Any] = field(compare=False, hash=False)

	@property
	def skipped(self) -> bool:
		return bool(self.entry["skipped"])

	@property
	def faded(self) -> bool:
		"""Rien n'en joue ce jour-là : un autre événement la couvre."""
		return (self.plays == ()) and (not self.skipped)


FOND_SHARE = 0.3
"""La part de la couleur dans le fond estompé d'un bloc, comme color-mix(… 30%, #ffffff) de la feuille de style."""
FRAME_SHARE = 0.7
"""La part de la couleur dans son cadre, plus sombre, comme color-mix(…, #000000 30%)."""


def _plays(entry: dict[str, Any], start: datetime, end: datetime) -> tuple[tuple[datetime, datetime], ...]:
	found = []
	for moment in entry["on_air"]:
		departure, arrival = max(moment["start"], start), min(moment["end"], end)
		if departure < arrival:
			found.append((departure, arrival))
	return tuple(found)


def blocks(found: list[dict[str, Any]], first: date) -> list[Block]:
	"""Les blocs de la semaine de first : une occurrence qui passe minuit en donne un par jour qu'elle touche."""
	found_blocks = []
	for ordinal, entry in enumerate(found):
		whole_day = entry["end"] - entry["start"] >= ONE_DAY
		for offset in range(WEEK):
			day = first + timedelta(days=offset)
			start, end = max(entry["start"], midnight(day)), min(entry["end"], midnight(day + ONE_DAY))
			if start < end:
				found_blocks.append(Block(ordinal, day, start, end, _plays(entry, start, end), whole_day, entry))
	return sorted(
		found_blocks, key=lambda b: (b.day, b.start, RANKS[Priority(b.entry["priority"])], b.entry["id"], b.ordinal)
	)


def _minutes(day: date, moment: datetime) -> float:
	"""Les minutes de moment depuis le début de day, à l'heure murale du poste : 1440 pour la fin du jour, même un jour
	de changement d'heure."""
	if moment >= midnight(day + ONE_DAY):
		return MINUTES
	local = moment.astimezone()
	return local.hour * 60 + local.minute + local.second / 60


def short_title(day: date) -> str:
	"""Le nom court d'un jour, sur un écran étroit : « mer. 18/11 »."""
	return _("{weekday}. {day:02d}/{month:02d}").format(
		weekday=DAY_NAMES[day.weekday()][:3], day=day.day, month=day.month
	)


def _percent(fraction: float) -> str:
	return f"{fraction * 100:.4f}%"


def _schedule(block: Block) -> str:
	"""Les heures de l'occurrence, avec ses jours quand elle en touche plusieurs."""
	start, end = block.entry["start"], block.entry["end"]
	if (end - start <= ONE_DAY) and ((start.date() == end.date()) or (end == midnight(start.date() + ONE_DAY))):
		return f"{hour(start)} – {end_hour(start, end)}"
	return f"{day_title(start.date())} {hour(start)} – {day_title(end.date())} {hour(end)}"


def _what_plays(block: Block) -> str:
	if block.skipped:
		return _("Skipped session")
	if block.plays == ((block.start, block.end),):
		return _("Plays in full")
	if block.plays == ():
		return _("Hidden in full {mask}").format(mask=MASK)
	moment_list = []
	for start, end in block.plays:
		moment_list.append(
			_("from {schedule} to {schedule2}").format(schedule=hour(start), schedule2=end_hour(start, end))
		)
	return _("Plays {moments}; hidden the rest of the time {mask}").format(
		moments=_(" and ").join(moment_list), mask=MASK
	)


def tooltip(block: Block) -> str:
	"""L'infobulle d'un bloc : l'événement et sa priorité, ses heures, sa suppression et ce qui en joue ce jour-là."""
	entry = block.entry
	label = PRIORITIES.get(Priority(entry["priority"]), entry["priority"])
	lines = [f"{entry['name']} — {label}", _schedule(block)]
	if entry["deleted"]:
		lines.append(_("Deleted event"))
	lines.append(_what_plays(block))
	return "\n".join(lines)


def _vevent(block: Block) -> str:
	"""Le texte d'un bloc, en hCalendar."""
	entry = block.entry
	classes = ["vevent", "h-event", entry["priority"]]
	if block.faded:
		classes.append("couvert")
	if block.skipped:
		classes.append("saute")
	label = PRIORITIES.get(Priority(entry["priority"]), entry["priority"])
	title = escape(tooltip(block)).replace("\n", "&#10;")
	return (
		f'<div class="{" ".join(classes)}" title="{title}">'
		f'<span class="summary p-name">{escape(entry["name"])}</span> '
		f'<time class="dtstart dt-start" datetime="{block.start.isoformat()}">{hour(block.start)}</time>–'
		f'<time class="dtend dt-end" datetime="{block.end.isoformat()}">{end_hour(block.start, block.end)}</time> '
		f'<span class="category p-category">{escape(label)}</span>{remark(entry)}</div>'
	)


def _block(block: Block, place: tuple[str, str, str, str], pattern: str) -> str:
	"""Un bloc à sa place (x, y, largeur, hauteur) : estompé, plein à ses moments à l'antenne, de haut en bas dans les
	heures, de gauche à droite dans la bande, hachuré s'il est sauté, puis son cadre et son texte."""
	x, y, width, height = place
	# La couleur d'un plugin passe par les attributs du SVG, que la feuille de style ne remplace pas : l'intranet
	# n'écrit aucun style dans la page (https://github.com/dascritch/machincast/issues/635).
	colour = block.entry.get("colour")
	classes = ["bloc", block.entry["priority"]]
	fond = fill = stroke = ""
	if colour is not None:
		background = mixed(colour, FOND_SHARE)
		classes.append("colore")
		if readable_text(background) == WHITE:
			classes.append("texte-clair")
		fond = f' fill="{background}"'
		fill = f' fill="{colour}"'
		stroke = f' stroke="{mixed(colour, FRAME_SHARE, BLACK)}"'
	parts = [
		f'<svg class="{" ".join(classes)}" x="{x}" y="{y}" width="{width}" height="{height}">',
		f'<rect class="fond" width="100%" height="100%"{fond}/>',
	]
	for start, end in block.plays:
		if block.whole_day:
			left, right = _minutes(block.day, start) / MINUTES, _minutes(block.day, end) / MINUTES
			parts.append(
				f'<rect class="antenne" x="{_percent(left)}" width="{_percent(right - left)}" height="100%"{fill}/>'
			)
		else:
			length = (block.end - block.start).total_seconds()
			top = (start - block.start).total_seconds() / length
			bottom = (end - block.start).total_seconds() / length
			parts.append(
				f'<rect class="antenne" y="{_percent(top)}" height="{_percent(bottom - top)}" width="100%"{fill}/>'
			)
	if block.skipped:
		parts.append(f'<rect class="hachures" width="100%" height="100%" fill="url(#{pattern})"/>')
	parts += [
		f'<rect class="cadre" width="100%" height="100%"{stroke}/>',
		f'<foreignObject width="100%" height="100%">{_vevent(block)}</foreignObject>',
		"</svg>",
	]
	return "".join(parts)


def _hatching(identifier: str) -> str:
	return (
		f'<defs><pattern id="{identifier}" width="8" height="8" patternUnits="userSpaceOnUse">'
		'<path d="M0,8 L8,0" stroke="#000000" stroke-opacity="0.35" stroke-width="1.5"/></pattern></defs>'
	)


def _separations(height: str) -> list[str]:
	lines = []
	for index in range(WEEK + 1):
		x = _percent(index / WEEK)
		lines.append(f'<line class="separation" x1="{x}" x2="{x}" y1="0" y2="{height}"/>')
	return lines


def _today_class(day: date, now: datetime) -> str:
	if day == now.date():
		return " aujourdhui"
	return ""


def _header(days: list[date], found: list[Block], now: datetime) -> str:
	"""Le nom des jours, et la bande de la journée entière."""
	by_day: dict[date, list[Block]] = {}
	for block in found:
		if block.whole_day:
			by_day.setdefault(block.day, []).append(block)
	rows = 1
	for day_blocks in by_day.values():
		rows = max(rows, len(day_blocks))
	height = NAME_HEIGHT + rows * LINE_HEIGHT + GAP
	parts = [
		'<div class="entete">',
		'<div class="coin"></div>',
		f'<svg class="noms" width="100%" height="{height}">',
		_hatching("hachures-bande"),
		*_separations("100%"),
	]
	for index, day in enumerate(days):
		for kind, label in (("nom-du-jour", day_title(day)), ("nom-court", short_title(day))):
			parts.append(
				f'<text class="{kind}{_today_class(day, now)}" x="{_percent((index + 0.5) / WEEK)}" y="17" '
				f'text-anchor="middle">{escape(label)}</text>'
			)
		parts.append(f'<g class="bande" aria-label="{escape(day_title(day))}">')
		for rank, block in enumerate(by_day.get(day, [])):
			place = (
				_percent(index / WEEK),
				str(NAME_HEIGHT + rank * LINE_HEIGHT + 1),
				_percent(1 / WEEK),
				str(LINE_HEIGHT - 2),
			)
			parts.append(_block(block, place, "hachures-bande"))
		parts.append("</g>")
	parts += ["</svg>", "</div>"]
	return "\n".join(parts)


def _hours() -> str:
	parts = [f'<svg class="heures" width="100%" height="{24 * HOUR_HEIGHT}">']
	for value in range(24):
		parts.append(
			f'<text class="heure" x="100%" dx="-6" y="{_percent(value / 24)}" dy="14" text-anchor="end">'
			f"{value:02d}:00</text>"
		)
	parts.append("</svg>")
	return "\n".join(parts)


def _day(index: int, day: date, found: list[Block], now: datetime) -> str:
	"""Les blocs des heures d'un jour, côte à côte quand ils se chevauchent."""
	day_blocks = []
	for block in found:
		if (block.day == day) and (not block.whole_day):
			day_blocks.append(block)
	places = columns(day_blocks)
	parts = [f'<g class="jour{_today_class(day, now)}" aria-label="{escape(day_title(day))}">']
	for block in day_blocks:
		column, count = places[block]
		top, bottom = _minutes(day, block.start) / MINUTES, _minutes(day, block.end) / MINUTES
		place = (
			_percent((index + column / count) / WEEK),
			_percent(top),
			_percent(1 / (WEEK * count)),
			_percent(bottom - top),
		)
		parts.append(_block(block, place, "hachures"))
	parts.append("</g>")
	return "\n".join(parts)


def _grid(days: list[date], found: list[Block], now: datetime) -> str:
	"""Les heures de chaque jour, et le trait de l'heure actuelle."""
	parts = [f'<svg class="jours" width="100%" height="{24 * HOUR_HEIGHT}">', _hatching("hachures")]
	for value in range(25):
		y = _percent(value / 24)
		parts.append(f'<line class="trait" x1="0" x2="100%" y1="{y}" y2="{y}"/>')
	parts += _separations("100%")
	for index, day in enumerate(days):
		parts.append(_day(index, day, found, now))
	if now.date() in days:
		index = days.index(now.date())
		y = _percent(_minutes(now.date(), now) / MINUTES)
		parts.append(
			f'<line class="maintenant" x1="{_percent(index / WEEK)}" x2="{_percent((index + 1) / WEEK)}" '
			f'y1="{y}" y2="{y}"/>'
		)
	parts.append("</svg>")
	return "\n".join(parts)


def week(found: list[dict[str, Any]], first: date, now: datetime) -> str:
	"""La semaine de first en grille horaire, telle qu'elle est à now, à l'heure du poste."""
	days = []
	for offset in range(WEEK):
		days.append(first + timedelta(days=offset))
	now = now.astimezone()
	found_blocks = blocks(found, first)
	return "\n".join(
		(
			'<div class="calendrier">',
			_header(days, found_blocks, now),
			f'<div class="defilement" id="grille" data-premiere-heure="{FIRST_HOUR}">',
			_hours(),
			_grid(days, found_blocks, now),
			"</div>",
			"</div>",
		)
	)
