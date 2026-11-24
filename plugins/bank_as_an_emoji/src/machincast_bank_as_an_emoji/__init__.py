"""La banque en emoji : un emoji au début du nom interne d'une banque, « 🌟 Publicités », pour la lire d'un coup d'œil
dans les tableaux d'airplay et des sonores à venir, qui montrent son nom interne
(https://github.com/dascritch/machincast/issues/505).

Dans Machin interface, la fiche d'une banque choisit son emoji devant son nom interne, qui ne le montre pas
(machincast_bank_as_an_emoji.section) ; l'emoji est rangé dans les premiers caractères du nom interne, suivi d'une
espace : le plugin n'a ni table ni colonne.
"""

from typing import Any

from machincast.plugins import Plugin


def register(plugin: Plugin) -> None:
	"""S'abonne au point de la fiche d'une banque, dans Machin interface seulement."""
	if plugin.context.executable == "Machin_interface":
		from machincast_bank_as_an_emoji import section

		def card_section(data: Any) -> object:
			return section.EmojiSection(data["card"], data["parent"])

		plugin.on("interface.bank_card", card_section)
