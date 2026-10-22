"""Scénarios de la playlist immédiate du binaire lecture (https://github.com/dascritch/machincast/issues/228).

La diffusion tourne sur le moteur simulé (tests/etapes_diffusion.py, MoteurSimuleNote), qui suit l'horloge du
binaire. Les sonores à venir se lisent dans la diffusion : la socket d'état les publie (tests/test_etat.py).
"""

from pathlib import Path

from pytest_bdd import parsers, scenarios, then, when

from tests.etapes_diffusion import Banc, Connexion, emission_des_sonores, passages

scenarios("playlist_immediate.feature")


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("le sonore « {nom} » est désactivé"))
def desactiver(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("UPDATE sonores SET etat = 'desactive' WHERE titre = %s", (nom,))


@when(parsers.parse("le fichier de test du sonore « {nom} » disparaît"))
def fichier_disparu(banc: Banc, nom: str) -> None:
	"""La copie de test du fichier, dans le répertoire temporaire du scénario, est effacée par le test lui-même."""
	banc.fichiers[nom].unlink()


@when(
	parsers.re(
		r"(?P<genre>l'émission|le spécial) « (?P<nom>[^»]+) » de (?P<debut>[\d:]+) à (?P<fin>[\d:]+),"
		r" avec les sonores (?P<liste_sonores>.+), est ajoutée? à la grille"
	)
)
def ajouter_a_la_grille(
	banc: Banc,
	base_vide: Connexion,
	tmp_path: Path,
	genre: str,
	nom: str,
	debut: str,
	fin: str,
	liste_sonores: str,
) -> None:
	emission_des_sonores(banc, base_vide, tmp_path, genre, nom, debut, fin, liste_sonores)


# ─── Alors ─────────────────────────────────────────────────


@then("les passages, à partir du deuxième, sont les sonores notés")
def engages(base_vide: Connexion, notes: list[str]) -> None:
	joues = [p[0] for p in passages(base_vide)]
	assert len(notes) == 6, notes
	assert joues[1 : 1 + len(notes)] == notes, (joues, notes)
