"""Suppression d'un élément depuis sa fiche (https://github.com/dascritch/machincast/issues/33, spec § 8.9).

Supprimer un sonore, une banque, une séquence ou un événement le retire des listes où il figure, et le marque
« supprimé », avec l'instant de la demande (supprime_le) : il reste en base jusqu'à sa péremption, hors des listes, de
la recherche et de la grille, et se restaure depuis sa fiche (restaurer,
https://github.com/dascritch/machincast/issues/267). Restauré, il ne revient pas dans les listes d'où il avait été
retiré. Un événement supprimé ne secourt plus aucun stream. Un feed quitte la base. Jamais un fichier sonore ni un
répertoire, qui restent à leur place, intacts (https://github.com/dascritch/machincast/issues/96). L'historique de
diffusion garde ses passages.

La question de confirmation dit où l'élément figure, et quelle liste n'aurait plus rien après son retrait.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
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
	differee: bool = True
	"""Supprimé, il reste en base, marqué, jusqu'à sa péremption ; sinon, il quitte la base."""

	@property
	def objet(self) -> str:
		"""« le » ou « la » : le pronom qui le reprend."""
		if self.accord == "e":
			return "la"
		return "le"


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
	"feed": Genre("feeds", "le feed", "Il", "", "", (), "Aucun stream ne le suit.", "nom", False, False),
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
	lignes.append(
		"Il ne joue plus ; sa liste de lecture reste avec lui. Ses sonores, banques et séquences restent en base."
	)
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
	lignes = [f"Supprimer {decrit.article} « {nom} » ?"]
	if not decrit.differee:
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
	if decrit.differee:
		lignes.append(
			f"Marqué{decrit.accord} « supprimé{decrit.accord} », {decrit.pronom.lower()} se restaure depuis sa fiche."
		)
	return f"Supprimer {decrit.article}", "\n".join(lignes)


def supprimer(connexion: Connexion, genre: str, identifiant: int, instant: datetime) -> None:
	"""Dans la transaction en cours : retire l'élément des listes qui le contiennent, et le marque « supprimé » à cet
	instant ; un événement ne secourt plus aucun stream. Un feed quitte la base."""
	decrit = GENRES[genre]
	if not decrit.differee:
		connexion.execute(f"DELETE FROM {decrit.table} WHERE id = %s", (identifiant,))  # noqa: S608
		return
	for contenant in decrit.contenants:
		_table, elements, _parent, _nommer, _vide = CONTENANTS[contenant]
		connexion.execute(f"DELETE FROM {elements} WHERE {decrit.colonne} = %s", (identifiant,))  # noqa: S608
	if genre == "événement":
		connexion.execute(
			"UPDATE sonores SET secours_evenement_id = NULL WHERE secours_evenement_id = %s", (identifiant,)
		)
	connexion.execute(
		f"UPDATE {decrit.table} SET supprime_le = %s WHERE id = %s",  # noqa: S608
		(instant, identifiant),
	)


def supprime_le(connexion: Connexion, genre: str, identifiant: int) -> datetime | None:
	"""L'instant de la demande de suppression ; None pour un élément qui n'est pas supprimé, ou qui ne l'est jamais
	qu'en quittant la base."""
	decrit = GENRES[genre]
	if not decrit.differee:
		return None
	ligne = connexion.execute(
		f"SELECT supprime_le FROM {decrit.table} WHERE id = %s",  # noqa: S608
		(identifiant,),
	).fetchone()
	if (ligne is None) or (not isinstance(ligne[0], datetime)):
		return None
	return ligne[0]


def marque(genre: str, instant: datetime, peremption: int) -> str:
	"""Ce que dit la fiche d'un élément supprimé : quand il l'a été, et après quel jour Machin purge l'efface de la
	base, peremption jours plus tard (https://github.com/dascritch/machincast/issues/268)."""
	decrit = GENRES[genre]
	efface = (instant + timedelta(days=peremption)).astimezone()
	return (
		f"Supprimé{decrit.accord} le {instant.astimezone():%d/%m/%Y à %H:%M}, effacé{decrit.accord} de la base après le"
		f" {efface:%d/%m/%Y} : « Restaurer » {decrit.objet} remet en service."
	)


def restaurer(connexion: Connexion, genre: str, identifiant: int) -> None:
	"""Dans la transaction en cours : l'élément n'est plus supprimé, sans revenir dans les listes d'où il avait été
	retiré. Lève Empechee si un autre élément a repris son nom, ou son emplacement."""
	decrit = GENRES[genre]
	colonne = "emplacement"
	if genre != "sonore":
		colonne = decrit.nom
	pris = connexion.execute(
		f"SELECT o.{colonne} FROM {decrit.table} s JOIN {decrit.table} o ON o.{colonne} = s.{colonne}"  # noqa: S608
		" AND o.id <> s.id AND o.supprime_le IS NULL WHERE s.id = %s",
		(identifiant,),
	).fetchone()
	if pris is not None:
		qui = f"{_un_autre(decrit)} s'appelle déjà « {pris[0]} »"
		if genre == "sonore":
			qui = f"un autre sonore a déjà ce fichier, {pris[0]}"
		raise Empechee(f"Restauration impossible : {qui}.")
	connexion.execute(f"UPDATE {decrit.table} SET supprime_le = NULL WHERE id = %s", (identifiant,))  # noqa: S608


def _un_autre(decrit: Genre) -> str:
	"""« une autre banque », « un autre événement »…"""
	nom = decrit.article.split(" ", 1)[-1].removeprefix("l'")
	if decrit.accord == "e":
		return f"une autre {nom}"
	return f"un autre {nom}"
