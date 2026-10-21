"""Actions sur plusieurs sonores ou plusieurs banques à la fois (https://github.com/dascritch/machincast/issues/114,
spec § 8.2).

Les listes des sonores et des banques (machincast.interface.listes) proposent ces actions au clic droit sur leur
sélection ; la fenêtre (machincast.interface.fenetre) fait choisir des banques s'il le faut, demande confirmation
(dialogues.confirmer_action), puis exécute l'action dans une transaction, avec le rôle de l'interface.

- Activer, désactiver : l'état des sonores choisis, comme dans leur fiche ; un sonore en aperçu reste en aperçu,
  jusqu'à sa vérification.
- Ajouter à des banques : chaque sonore à la fin de chaque banque choisie, sauf s'il y est déjà.
- Retirer de banques : parmi les banques où figure l'un des sonores ; les positions restantes se resserrent. Un
  sonore dont le fichier est dans un répertoire de la banque y reviendra à la prochaine indexation.
- Audit complet demandé (sonores.audit_demande) : la prochaine indexation, même rapide, revérifie en entier les
  fichiers marqués (machincast.indexation.verification) ; un stream n'est jamais vérifié.
- Masquage de l'artiste et du titre des banques choisies : masqués, affichés, ou hérités du sonore.

Chaque action rend la phrase qu'annonce la barre d'état : ce qui a réellement changé.
"""

from collections.abc import Callable
from dataclasses import dataclass

import psycopg
from psycopg.rows import TupleRow

Connexion = psycopg.Connection[TupleRow]
REVERIFIER = "La prochaine indexation, même rapide, les revérifiera en entier."


def nombre(quantite: int, singulier: str, pluriel: str) -> str:
	"""« 1 sonore », « 2 sonores », « 0 sonore »."""
	if quantite > 1:
		return f"{quantite} {pluriel}"
	return f"{quantite} {singulier}"


def _sonores(quantite: int) -> str:
	return nombre(quantite, "sonore", "sonores")


def _banques(quantite: int) -> str:
	return nombre(quantite, "banque", "banques")


def _noms(noms: list[str]) -> str:
	return ", ".join(f"« {nom} »" for nom in noms)


def _aux_banques(noms: list[str]) -> str:
	if len(noms) == 1:
		return f"à la banque {_noms(noms)}"
	return f"aux banques {_noms(noms)}"


def _des_banques(noms: list[str]) -> str:
	if len(noms) == 1:
		return f"de la banque {_noms(noms)}"
	return f"des banques {_noms(noms)}"


def _identifiants(rangees: list[TupleRow]) -> set[int]:
	return {int(str(rangee[0])) for rangee in rangees}


@dataclass(frozen=True)
class Action:
	cle: str
	texte: str
	"""L'entrée du menu ; « … » quand un choix de banques la suit."""
	question: Callable[[int, list[str]], str]
	"""Le texte de la confirmation, selon le nombre d'éléments choisis et les noms des banques choisies."""
	executer: Callable[[Connexion, list[int], list[int]], str]
	"""Dans une transaction : l'action sur les éléments et les banques choisies ; l'annonce de la barre d'état."""
	choix: str = ""
	"""« toutes » : choisir parmi toutes les banques ; « leurs » : parmi celles des sonores ; « » : aucun choix."""

	@property
	def titre(self) -> str:
		"""Le titre de la confirmation : l'entrée du menu, sans « … »."""
		return self.texte.removesuffix("…")


# ─── Sonores ───────────────────────────────────────────────


def _changer_d_etat(etat: str, fait: str, faits: str) -> Callable[[Connexion, list[int], list[int]], str]:
	def executer(connexion: Connexion, sonores: list[int], _banques: list[int]) -> str:
		changes = connexion.execute(
			"UPDATE sonores SET etat = %s WHERE id = ANY(%s) AND etat NOT IN ('apercu', %s) RETURNING id",
			(etat, sonores, etat),
		).fetchall()
		return f"{nombre(len(changes), fait, faits)}."

	return executer


def _question_d_etat(verbe: str) -> Callable[[int, list[str]], str]:
	def question(quantite: int, _noms_des_banques: list[str]) -> str:
		return f"{verbe} {_sonores(quantite)} ? Un sonore en aperçu reste en aperçu."

	return question


def _ajouter(connexion: Connexion, sonores: list[int], banques: list[int]) -> str:
	ajoutes: set[int] = set()
	touchees: set[int] = set()
	for banque in banques:
		presents = _identifiants(
			connexion.execute(
				"SELECT sonore_id FROM banques_sonores WHERE banque_id = %s FOR UPDATE", (banque,)
			).fetchall()
		)
		nouveaux = [sonore for sonore in sonores if sonore not in presents]
		if nouveaux == []:
			continue
		ligne = connexion.execute(
			"SELECT COALESCE(MAX(position), 0) FROM banques_sonores WHERE banque_id = %s", (banque,)
		).fetchone()
		assert ligne is not None
		fin = int(str(ligne[0]))
		with connexion.cursor() as curseur:
			curseur.executemany(
				"INSERT INTO banques_sonores (banque_id, sonore_id, position) VALUES (%s, %s, %s)",
				[(banque, sonore, fin + rang) for rang, sonore in enumerate(nouveaux, start=1)],
			)
		ajoutes |= set(nouveaux)
		touchees.add(banque)
	return f"{nombre(len(ajoutes), 'sonore ajouté', 'sonores ajoutés')} {_a(len(touchees))}."


def _a(banques: int) -> str:
	return f"à {nombre(banques, 'banque', 'banques')}"


def _retirer(connexion: Connexion, sonores: list[int], banques: list[int]) -> str:
	retires = connexion.execute(
		"DELETE FROM banques_sonores WHERE sonore_id = ANY(%s) AND banque_id = ANY(%s) RETURNING sonore_id, banque_id",
		(sonores, banques),
	).fetchall()
	touchees = sorted({int(str(banque)) for _sonore, banque in retires})
	# Les positions restantes se resserrent ; leur unicité n'est vérifiée qu'en fin de transaction.
	connexion.execute(
		"UPDATE banques_sonores bs SET position = r.rang FROM ("
		" SELECT banque_id, sonore_id, row_number() OVER (PARTITION BY banque_id ORDER BY position) AS rang"
		" FROM banques_sonores WHERE banque_id = ANY(%s)) r"
		" WHERE bs.banque_id = r.banque_id AND bs.sonore_id = r.sonore_id",
		(touchees,),
	)
	nombre_de_sonores = len(_identifiants(retires))
	de = f"de {nombre(len(touchees), 'banque', 'banques')}"
	return f"{nombre(nombre_de_sonores, 'sonore retiré', 'sonores retirés')} {de}."


def _annonce_d_audit(marques: int) -> str:
	return f"Audit complet demandé pour {nombre(marques, 'sonore', 'sonores')}, à la prochaine indexation."


def _demander_l_audit(connexion: Connexion, sonores: list[int], _banques: list[int]) -> str:
	marques = connexion.execute(
		"UPDATE sonores SET audit_demande = true WHERE id = ANY(%s) AND type = 'fichier' RETURNING id", (sonores,)
	).fetchall()
	return _annonce_d_audit(len(marques))


def _question_d_audit(quantite: int, _noms_des_banques: list[str]) -> str:
	reverifier = REVERIFIER
	if quantite == 1:
		reverifier = "La prochaine indexation, même rapide, le revérifiera en entier."
	return f"Demander l'audit complet de {_sonores(quantite)} ? {reverifier}"


SONORES: tuple[Action, ...] = (
	Action(
		"activer", "Activer", _question_d_etat("Activer"), _changer_d_etat("actif", "sonore activé", "sonores activés")
	),
	Action(
		"desactiver",
		"Désactiver",
		_question_d_etat("Désactiver"),
		_changer_d_etat("desactive", "sonore désactivé", "sonores désactivés"),
	),
	Action(
		"ajouter",
		"Ajouter à des banques…",
		lambda quantite, noms: (
			f"Ajouter {_sonores(quantite)} {_aux_banques(noms)} ?"
			" Un sonore déjà dans une banque n'y est pas ajouté une seconde fois."
		),
		_ajouter,
		"toutes",
	),
	Action(
		"retirer",
		"Retirer de banques…",
		lambda quantite, noms: (
			f"Retirer {_sonores(quantite)} {_des_banques(noms)} ?"
			" Un sonore dont le fichier est dans un répertoire d'une banque y reviendra à la prochaine indexation."
		),
		_retirer,
		"leurs",
	),
	Action("audit", "Demander un audit complet", _question_d_audit, _demander_l_audit),
)


# ─── Banques ───────────────────────────────────────────────


def _demander_l_audit_des_banques(connexion: Connexion, banques: list[int], _choisies: list[int]) -> str:
	marques = connexion.execute(
		"UPDATE sonores SET audit_demande = true WHERE type = 'fichier'"
		" AND id IN (SELECT sonore_id FROM banques_sonores WHERE banque_id = ANY(%s)) RETURNING id",
		(banques,),
	).fetchall()
	return _annonce_d_audit(len(marques))


def _masquer(valeur: bool | None, etat: str) -> Callable[[Connexion, list[int], list[int]], str]:
	def executer(connexion: Connexion, banques: list[int], _choisies: list[int]) -> str:
		changees = connexion.execute(
			"UPDATE banques SET masquer_metadonnees = %s WHERE id = ANY(%s) RETURNING id", (valeur, banques)
		).fetchall()
		return f"Artiste et titre {etat} pour {nombre(len(changees), 'banque', 'banques')}."

	return executer


BANQUES: tuple[Action, ...] = (
	Action(
		"audit",
		"Demander l'audit complet de leurs sonores",
		lambda quantite, _noms: f"Demander l'audit complet des sonores de {_banques(quantite)} ? {REVERIFIER}",
		_demander_l_audit_des_banques,
	),
	Action(
		"masquer",
		"Masquer l'artiste et le titre",
		lambda quantite, _noms: f"Masquer l'artiste et le titre des sonores de {_banques(quantite)} ?",
		_masquer(True, "masqués"),
	),
	Action(
		"afficher",
		"Afficher l'artiste et le titre",
		lambda quantite, _noms: f"Afficher l'artiste et le titre des sonores de {_banques(quantite)} ?",
		_masquer(False, "affichés"),
	),
	Action(
		"heriter",
		"Artiste et titre hérités du sonore",
		lambda quantite, _noms: f"Laisser au sonore le masquage de l'artiste et du titre de {_banques(quantite)} ?",
		_masquer(None, "hérités du sonore"),
	),
)

ACTIONS: dict[str, tuple[Action, ...]] = {"sonore": SONORES, "banque": BANQUES}
"""Les actions sur la sélection de chaque liste ; les autres listes ne sélectionnent qu'une ligne."""


def action(genre: str, cle: str) -> Action:
	(trouvee,) = [action for action in ACTIONS[genre] if action.cle == cle]
	return trouvee


def banques_des_sonores(connexion: Connexion, sonores: list[int]) -> list[int]:
	"""Les banques où figure l'un des sonores, par nom. À appeler dans une transaction."""
	return [
		int(str(banque))
		for (banque,) in connexion.execute(
			"SELECT b.id FROM banques b WHERE b.id IN (SELECT banque_id FROM banques_sonores WHERE sonore_id = ANY(%s))"
			" ORDER BY b.nom_interne, b.id",
			(sonores,),
		)
	]


def noms_des_banques(connexion: Connexion, banques: list[int]) -> list[str]:
	"""Les noms des banques, dans l'ordre donné. À appeler dans une transaction."""
	noms = {
		int(str(banque)): str(nom)
		for banque, nom in connexion.execute("SELECT id, nom_interne FROM banques WHERE id = ANY(%s)", (banques,))
	}
	return [noms[banque] for banque in banques if banque in noms]
