"""Suppression d'un élément depuis sa fiche (https://github.com/dascritch/machincast/issues/33, spec § 8.9).

Supprimer un sonore, une banque, une séquence ou un événement supprime sa ligne en base, et le retire des listes où il
figure (les clés étrangères en cascade) : jamais un fichier sonore ni un répertoire, qui restent à leur place, intacts
(https://github.com/dascritch/machincast/issues/96). L'historique de diffusion garde ses passages (les références de
airplay passent à NULL), comme les streams qu'un événement de secours supprimé secourait.

La question de confirmation dit où l'élément figure, et quelle liste n'aurait plus rien après son retrait.
"""

from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.interface import affichage

Connexion = psycopg.Connection[TupleRow]


@dataclass(frozen=True)
class Genre:
	table: str
	article: str
	"""« le sonore », « la banque »…"""
	pronom: str
	"""« Il » ou « Elle »."""
	accord: str
	"""« » ou « e » : retiré, retirée."""
	colonne: str
	"""Colonne qui désigne l'élément dans les listes qui le contiennent."""
	contenants: tuple[str, ...]
	"""Genres des listes qui peuvent le contenir."""
	aucun: str
	"""Phrase pour un élément qui ne figure nulle part."""
	nom: str = "nom_interne"
	"""Colonne de son nom."""
	historique: bool = True
	"""L'historique de diffusion le cite : la question rappelle qu'il garde ses passages."""


GENRES = {
	"sonore": Genre(
		"sonores",
		"le sonore",
		"Il",
		"",
		"sonore_id",
		("banque", "séquence", "événement"),
		"Il ne figure dans aucune banque, aucune séquence ni aucun événement.",
	),
	"banque": Genre(
		"banques",
		"la banque",
		"Elle",
		"e",
		"banque_id",
		("séquence", "événement"),
		"Elle ne figure dans aucune séquence ni aucun événement.",
	),
	"séquence": Genre(
		"sequences", "la séquence", "Elle", "e", "sequence_id", ("événement",), "Elle ne figure dans aucun événement."
	),
	"événement": Genre("evenements", "l'événement", "Il", "", "", (), ""),
	"feed": Genre("feeds", "le feed", "Il", "", "", (), "Aucun stream ne le suit.", "nom", False),
}
CONTENANTS = {
	"banque": ("banques", "banques_sonores", "banque_id", "de la banque", "qui n'aura plus aucun sonore"),
	"séquence": ("sequences", "sequences_elements", "sequence_id", "de la séquence", "qui n'aura plus aucun élément"),
	"événement": (
		"evenements",
		"evenements_elements",
		"evenement_id",
		"de l'événement",
		"qui n'aura plus rien à jouer",
	),
}
"""Pour chaque genre de liste : sa table, la table de ses éléments, la colonne qui la désigne, comment la nommer, et
ce qu'elle devient vide."""
HISTORIQUE = "L'historique de diffusion garde ses passages."


def _noms(lignes: list[TupleRow]) -> str:
	return ", ".join(f"« {ligne[0]} »" for ligne in lignes)


def _nom(connexion: Connexion, genre: str, identifiant: int) -> str | None:
	"""Le nom de l'élément ; None s'il n'est plus en base. Un sonore : artiste et titre, ou le nom de son fichier, ou
	l'adresse de son stream."""
	if genre != "sonore":
		ligne = connexion.execute(
			f"SELECT {GENRES[genre].nom} FROM {GENRES[genre].table} WHERE id = %s",  # noqa: S608
			(identifiant,),
		).fetchone()
		if ligne is None:
			return None
		return str(ligne[0])
	sonore = connexion.execute(
		"SELECT artiste, titre, emplacement, url_stream FROM sonores WHERE id = %s", (identifiant,)
	).fetchone()
	if sonore is None:
		return None
	return affichage.nom_du_sonore(*sonore)


def _retraits(connexion: Connexion, genre: str, identifiant: int) -> list[str]:
	"""Une ligne par liste qui contient l'élément : les banques, puis les séquences, puis les événements, par nom."""
	colonne = GENRES[genre].colonne
	lignes = []
	for contenant in GENRES[genre].contenants:
		table, elements, parent, nommer, vide = CONTENANTS[contenant]
		trouves = connexion.execute(
			f"SELECT c.nom_interne, NOT EXISTS (SELECT 1 FROM {elements} x WHERE x.{parent} = c.id"  # noqa: S608
			f" AND x.{colonne} IS DISTINCT FROM %s) FROM {table} c WHERE EXISTS (SELECT 1 FROM {elements} x"
			f" WHERE x.{parent} = c.id AND x.{colonne} = %s) ORDER BY c.nom_interne, c.id",
			(identifiant, identifiant),
		).fetchall()
		for nom, videe in trouves:
			ligne = f"• {nommer} « {nom} »"
			if videe:
				ligne = f"{ligne}, {vide}"
			lignes.append(ligne)
	return lignes


def _fichier(connexion: Connexion, identifiant: int) -> list[str]:
	"""Ce que devient le fichier d'un sonore : rien, il reste à sa place ; l'indexation le reprendra s'il est sous
	un répertoire de banque."""
	ligne = connexion.execute("SELECT emplacement FROM sonores WHERE id = %s", (identifiant,)).fetchone()
	if (ligne is None) or (ligne[0] is None):
		return []
	fichier = Path(str(ligne[0]))
	texte = f"Son fichier reste à sa place, intact : {fichier}."
	repertoires = connexion.execute(
		"SELECT b.nom_interne, r.repertoire FROM banques_repertoires r JOIN banques b ON b.id = r.banque_id"
		" ORDER BY b.nom_interne, r.repertoire"
	).fetchall()
	banques = list(
		dict.fromkeys(str(nom) for nom, repertoire in repertoires if fichier.is_relative_to(str(repertoire)))
	)
	if banques != []:
		quelles = f"de la banque « {banques[0]} »"
		if len(banques) > 1:
			quelles = f"des banques {', '.join(f'« {banque} »' for banque in banques)}"
		texte = (
			f"{texte} Il est dans un répertoire {quelles} : la prochaine indexation l'enregistrera de nouveau, comme un"
			" nouveau sonore."
		)
	return [texte]


def _suites(connexion: Connexion, genre: str, identifiant: int) -> list[str]:
	"""Ce qui reste après la suppression, propre à chaque genre."""
	if genre == "sonore":
		return _fichier(connexion, identifiant)
	if genre == "banque":
		repertoires = connexion.execute(
			"SELECT repertoire FROM banques_repertoires WHERE banque_id = %s ORDER BY repertoire", (identifiant,)
		).fetchall()
		if repertoires == []:
			return ["Ses sonores restent en base."]
		chemins = ", ".join(str(repertoire) for (repertoire,) in repertoires)
		return [
			f"Ses répertoires restent à leur place, avec leurs fichiers, intacts : {chemins}."
			" Ses sonores restent en base."
		]
	if genre == "séquence":
		return ["Ses sonores et ses banques restent en base."]
	if genre == "feed":
		return []
	streams = connexion.execute(
		"SELECT COALESCE(titre, url_stream) FROM sonores WHERE secours_evenement_id = %s ORDER BY 1", (identifiant,)
	).fetchall()
	lignes = []
	if len(streams) == 1:
		lignes.append(f"Il est l'événement de secours du stream {_noms(streams)}, qui n'en aura plus.")
	elif streams != []:
		lignes.append(f"Il est l'événement de secours des streams {_noms(streams)}, qui n'en auront plus.")
	lignes.append("Sa liste de lecture disparaît avec lui ; ses sonores, banques et séquences restent en base.")
	return lignes


class Empechee(Exception):
	"""L'élément ne peut pas être supprimé : le message dit pourquoi, et ce qu'il faut faire d'abord."""


def _empecher(connexion: Connexion, genre: str, identifiant: int) -> None:
	"""Un feed qu'un stream suit ne se supprime pas (feed_id ON DELETE RESTRICT)."""
	if genre != "feed":
		return
	streams = connexion.execute(
		"SELECT COALESCE(s.titre, m.url) FROM sonores s JOIN feeds m ON m.id = s.feed_id WHERE m.id = %s ORDER BY 1",
		(identifiant,),
	).fetchall()
	if streams != []:
		raise Empechee(
			f"Les streams {_noms(streams)} suivent ce feed : choisir pour eux une autre adresse avant de le supprimer."
		)


def question(connexion: Connexion, genre: str, identifiant: int) -> tuple[str, str] | None:
	"""Le titre et le texte de la question de suppression ; None si l'élément n'est plus en base. Lève Empechee pour
	un élément qui ne peut pas être supprimé. À appeler dans une transaction."""
	nom = _nom(connexion, genre, identifiant)
	if nom is None:
		return None
	_empecher(connexion, genre, identifiant)
	decrit = GENRES[genre]
	lignes = [f"Supprimer de la base {decrit.article} « {nom} » ?"]
	retraits = _retraits(connexion, genre, identifiant)
	if retraits != []:
		lignes.append(f"{decrit.pronom} en sera retiré{decrit.accord} :")
		lignes += [f"{retrait} ;" for retrait in retraits[:-1]]
		lignes.append(f"{retraits[-1]}.")
	elif decrit.aucun != "":
		lignes.append(decrit.aucun)
	lignes += _suites(connexion, genre, identifiant)
	if decrit.historique:
		lignes.append(HISTORIQUE)
	return f"Supprimer {decrit.article}", "\n".join(lignes)


def supprimer(connexion: Connexion, genre: str, identifiant: int) -> None:
	"""Supprime la ligne de l'élément, dans la transaction en cours ; les listes qui le contiennent le perdent."""
	connexion.execute(f"DELETE FROM {GENRES[genre].table} WHERE id = %s", (identifiant,))  # noqa: S608
