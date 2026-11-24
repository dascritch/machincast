"""L'emoji d'une banque, dans les premiers caractères de son nom interne, suivi d'une espace : « 🌟 Publicités »
(https://github.com/dascritch/machincast/issues/505).

Un emoji est une suite de pictogrammes, avec leurs sélecteurs de variante, leurs teintes de peau et leurs liants
(« 👩‍🔧 », « ☀️ », « 🇫🇷 ») ; un nom qui ne commence pas par un emoji suivi d'une espace n'en a pas.
"""

import re

PICTOGRAM = "[\U0001f000-\U0001faff☀-➿⬀-⯿⌀-⏿←-⇿〰〽㊗㊙©®‼⁉™ℹⓂ▪-◾⤴⤵]"
JOINED = "[️⃣‍\U0001f3fb-\U0001f3ff\U000e0020-\U000e007f]"
"""Ce qui suit ou lie les pictogrammes : sélecteur de variante, touche, liant, teintes de peau, étiquettes."""
EMOJI = re.compile(f"(?:{PICTOGRAM}{JOINED}*)+")
LEADING = re.compile(f"({EMOJI.pattern}) (.*)", re.DOTALL)

PALETTE = (
	"🌟",
	"📢",
	"💶",
	"🎙️",
	"📰",
	"🌦️",
	"🚗",
	"⏰",
	"🔔",
	"📻",
	"🎵",
	"🎶",
	"🎷",
	"🎸",
	"🥁",
	"🎹",
	"🎺",
	"🎻",
	"🎤",
	"🎧",
	"🌙",
	"☀️",
	"🌍",
	"💬",
	"❤️",
	"🔥",
	"⚡",
	"🎉",
	"🎄",
	"⚽",
	"🧒",
	"📚",
	"🎭",
	"🎬",
	"🚨",
	"🔇",
)
"""Les emojis proposés dans la fiche ; tout autre emoji peut s'y écrire ou s'y coller."""


def is_emoji(text: str) -> bool:
	return EMOJI.fullmatch(text) is not None


def split(name: str) -> tuple[str, str]:
	"""L'emoji du nom interne, ou une chaîne vide, et le reste du nom."""
	found = LEADING.fullmatch(name)
	if found is None:
		return "", name
	return found.group(1), found.group(2)


def joined(emoji: str, name: str) -> str:
	"""Le nom interne : l'emoji, une espace et le nom ; sans nom, rien, pour que la fiche le demande."""
	if (emoji == "") or (name.strip() == ""):
		return name
	return f"{emoji} {name}"
