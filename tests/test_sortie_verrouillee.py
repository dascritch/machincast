"""Scénarios du verrou des sorties PipeWire sur leur périphérique (https://github.com/dascritch/machincast/issues/345).

Les scénarios de comportement font tourner un PipeWire et un WirePlumber à part (BancPipeWire), dans des répertoires
temporaires : jamais ceux du poste. GStreamer les joint par PIPEWIRE_RUNTIME_DIR. Les sorties sont deux sorties
muettes (support.null-audio-sink) : la pré-écoute, périphérique par défaut, et l'antenne. Sans pipewire ni
wireplumber, ces scénarios sont ignorés.
"""

import json
import os
import shutil
import subprocess
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import audio
from machincast.configuration import Audio
from machincast.interface import moniteur

ATTENTE = 5.0
"""Secondes que WirePlumber a pour relier un flux."""
CALME = 1.5
"""Secondes au bout desquelles un flux qui n'est pas relié ne le sera pas."""
PROGRAMMES = {
	"Machin lecture": audio.ANTENNE,
	"la pré-écoute": audio.PREECOUTE,
	"l'essai de la sortie": audio.ESSAI,
}


def _pipewire_present() -> bool:
	return all(shutil.which(outil) for outil in ("pipewire", "wireplumber", "pw-cli", "pw-dump", "pw-metadata"))


class BancPipeWire:
	"""Un PipeWire et un WirePlumber à part, sans bus D-Bus, dans des répertoires temporaires."""

	def __init__(self, racine: Path) -> None:
		self.env = dict(os.environ)
		for nom in ("XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME"):
			chemin = racine / nom.lower()
			chemin.mkdir(mode=0o700)
			self.env[nom] = str(chemin)
		self.env["PIPEWIRE_RUNTIME_DIR"] = self.env["XDG_RUNTIME_DIR"]
		self.env.pop("DBUS_SESSION_BUS_ADDRESS", None)
		self.env.pop("PULSE_SERVER", None)
		self.journal = racine / "pipewire.log"
		self.processus: list[subprocess.Popen[bytes]] = []

	def demarrer(self) -> None:
		with self.journal.open("ab") as sortie:
			self.processus.append(subprocess.Popen(["pipewire"], env=self.env, stdout=sortie, stderr=sortie))
			self._attendre(lambda: self._commande("pw-cli", "info", "0").returncode == 0)
			self.processus.append(subprocess.Popen(["wireplumber"], env=self.env, stdout=sortie, stderr=sortie))
		# WirePlumber est prêt quand il a créé le pilote factice.
		self._attendre(lambda: self.noeud("Dummy-Driver") is not None)

	def arreter(self) -> None:
		for processus in reversed(self.processus):
			processus.terminate()
			try:
				processus.wait(timeout=5)
			except subprocess.TimeoutExpired:
				processus.kill()

	def _commande(self, *arguments: str) -> subprocess.CompletedProcess[str]:
		return subprocess.run(arguments, env=self.env, capture_output=True, text=True, timeout=10, check=False)

	@staticmethod
	def _attendre(condition: Callable[[], bool], delai: float = ATTENTE) -> bool:
		limite = time.monotonic() + delai
		while time.monotonic() < limite:
			if condition():
				return True
			time.sleep(0.1)
		return condition()

	def objets(self) -> list[dict[str, object]]:
		resultat = self._commande("pw-dump")
		if resultat.returncode != 0:
			return []
		objets: list[dict[str, object]] = json.loads(resultat.stdout)
		return objets

	def creer_sortie(self, nom: str) -> None:
		self._commande(
			"pw-cli",
			"create-node",
			"adapter",
			f"{{ factory.name=support.null-audio-sink node.name={nom} media.class=Audio/Sink object.linger=true"
			" audio.position=[ FL FR ] }",
		)
		self._attendre(lambda: self.noeud(nom) is not None)

	def detruire_sortie(self, nom: str) -> None:
		identifiant = self.noeud(nom)
		assert identifiant is not None, nom
		self._commande("pw-cli", "destroy", str(identifiant))
		self._attendre(lambda: self.noeud(nom) is None)

	def par_defaut(self, nom: str) -> None:
		self._commande("pw-metadata", "0", "default.configured.audio.sink", json.dumps({"name": nom}))

	def deplacer(self, flux: int, nom: str) -> None:
		"""Ce que font les réglages du son du poste pour déplacer un flux : la métadonnée target.object."""
		self._commande("pw-metadata", str(flux), "target.object", nom)

	def noeud(self, nom: str, cle: str = "node.name") -> int | None:
		for objet in self.objets():
			info = objet.get("info")
			if (
				(objet.get("type") == "PipeWire:Interface:Node")
				and (isinstance(info, dict))
				and (info.get("props", {}).get(cle) == nom)
			):
				return int(str(objet["id"]))
		return None

	def reliee_a(self, programme: str) -> set[str]:
		"""Les sorties auxquelles le flux du programme (application.name) est relié."""
		objets = self.objets()
		noms = {}
		flux = None
		for objet in objets:
			info = objet.get("info")
			if (objet.get("type") != "PipeWire:Interface:Node") or (not isinstance(info, dict)):
				continue
			proprietes = info.get("props", {})
			noms[objet["id"]] = proprietes.get("node.name")
			if proprietes.get("application.name") == programme:
				flux = objet["id"]
		reliees = set()
		for objet in objets:
			info = objet.get("info")
			lien = (objet.get("type") == "PipeWire:Interface:Link") and (isinstance(info, dict))
			if (lien) and (isinstance(info, dict)) and (info.get("output-node-id") == flux):
				reliees.add(str(noms.get(info.get("input-node-id"))))
		return reliees


@pytest.fixture
def contexte() -> SimpleNamespace:
	return SimpleNamespace(sortie=None, source=None, banc=None, pipelines=[], programme=None)


@pytest.fixture
def banc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, contexte: SimpleNamespace) -> Iterator[BancPipeWire]:
	"""Les pipelines s'arrêtent avant PipeWire : une sortie dont le serveur a disparu ne s'arrêterait plus."""
	if not _pipewire_present():
		pytest.skip("pipewire ou wireplumber absent")
	banc = BancPipeWire(tmp_path)
	banc.demarrer()
	monkeypatch.setenv("PIPEWIRE_RUNTIME_DIR", banc.env["PIPEWIRE_RUNTIME_DIR"])
	yield banc
	for pipeline in contexte.pipelines:
		pipeline.set_state(audio.Gst.State.NULL)
	banc.arreter()


# ─── Propriétés ────────────────────────────────────────────


@when(
	parsers.re(
		r"je crée la sortie « (?P<sortie>[^»]+) » de (?P<programme>.+), sur le périphérique « (?P<peripherique>[^»]*) »"
	)
)
def creer(contexte: SimpleNamespace, sortie: str, programme: str, peripherique: str) -> None:
	contexte.sortie = audio.creer_sortie(
		sortie,  # type: ignore[arg-type]
		(peripherique) or (None),
		presentation=PROGRAMMES[programme],
	)


@when(parsers.parse("je crée la source du VU-mètre de l'antenne « {peripherique} », sur PipeWire"))
def creer_la_source(contexte: SimpleNamespace, peripherique: str) -> None:
	bloc = moniteur.source_du_moniteur(Audio(sortie="pipewire", peripherique=peripherique, preecoute="casque"))
	(contexte.source,) = [element for element in bloc.children if element.get_factory().get_name() == "pipewiresrc"]


def _verrouillee(element: audio.Gst.Element, peripherique: str) -> None:
	proprietes = element.get_property("stream-properties")
	assert element.get_property("target-object") == peripherique
	assert proprietes is not None
	assert {cle: proprietes.get_value(cle) for cle in audio.VERROU} == dict.fromkeys(audio.VERROU, True)


@then(parsers.parse("la sortie vise « {peripherique} », sans repli, en l'attendant, sans déplacement"))
def sortie_verrouillee(contexte: SimpleNamespace, peripherique: str) -> None:
	_verrouillee(contexte.sortie, peripherique)


@then(parsers.parse("la source vise « {peripherique} », sans repli, en l'attendant, sans déplacement"))
def source_verrouillee(contexte: SimpleNamespace, peripherique: str) -> None:
	_verrouillee(contexte.source, peripherique)
	assert contexte.source.get_property("stream-properties").get_value("stream.capture.sink") is True


@then(parsers.parse("la sortie se présente toujours comme « {nom} »"))
def toujours_presentee(contexte: SimpleNamespace, nom: str) -> None:
	proprietes = contexte.sortie.get_property("stream-properties")
	assert (contexte.sortie.get_property("client-name"), proprietes.get_string("application.name")) == (nom, nom)


@then("la sortie n'a pas de verrou")
def sans_verrou(contexte: SimpleNamespace) -> None:
	sortie = contexte.sortie
	if sortie.find_property("stream-properties") is None:
		return
	proprietes = sortie.get_property("stream-properties")
	assert (proprietes is None) or (not any(proprietes.has_field(cle) for cle in audio.VERROU))


# ─── Comportement ──────────────────────────────────────────


@given(parsers.re(r"un PipeWire à part, avec la pré-écoute par défaut(?P<antenne> et l'antenne)?"))
def pipewire_a_part(contexte: SimpleNamespace, banc: BancPipeWire, antenne: str | None) -> None:
	banc.creer_sortie("preecoute")
	banc.par_defaut("preecoute")
	if antenne is not None:
		banc.creer_sortie("antenne")
	contexte.banc = banc


def _jouer(contexte: SimpleNamespace, sortie: audio.Gst.Element, programme: str) -> None:
	"""Un son continu sur la sortie : le flux existe même sans périphérique où aller.

	La source n'est pas en direct, comme les sonores de MachinCast : un pipeline à source en direct, sur un pipewiresink
	synchronisé, ne s'arrête plus avec le PipeWire à part.
	"""
	pipeline = audio.Gst.Pipeline.new(None)
	source = audio.Gst.ElementFactory.make("audiotestsrc", None)
	conversion = audio.Gst.ElementFactory.make("audioconvert", None)
	assert (source is not None) and (conversion is not None)
	for element in (source, conversion, sortie):
		pipeline.add(element)
	source.link(conversion)
	conversion.link(sortie)
	assert pipeline.set_state(audio.Gst.State.PLAYING) != audio.Gst.StateChangeReturn.FAILURE
	contexte.pipelines.append(pipeline)
	contexte.programme = programme
	contexte.banc._attendre(lambda: contexte.banc.noeud(programme, "application.name") is not None)


@when("l'antenne joue sur sa sortie")
def antenne_joue(contexte: SimpleNamespace) -> None:
	_jouer(contexte, audio.creer_sortie("pipewire", "antenne", presentation=audio.ANTENNE), audio.ANTENNE.programme)


@when("une sortie sans verrou joue sur l'antenne")
def sans_verrou_joue(contexte: SimpleNamespace) -> None:
	sortie = audio.Gst.ElementFactory.make("pipewiresink", None)
	assert sortie is not None
	sortie.set_property("target-object", "antenne")
	audio.presenter(sortie, audio.Presentation("Sans verrou", "Antenne"))
	_jouer(contexte, sortie, "Sans verrou")


@when(parsers.parse("le périphérique « {nom} » disparaît"))
def disparait(contexte: SimpleNamespace, nom: str) -> None:
	contexte.banc.detruire_sortie(nom)


@when(parsers.parse("le périphérique « {nom} » revient"))
def revient(contexte: SimpleNamespace, nom: str) -> None:
	contexte.banc.creer_sortie(nom)


@when(parsers.parse("les réglages du son du poste déplacent l'antenne vers « {nom} »"))
def deplacer(contexte: SimpleNamespace, nom: str) -> None:
	flux = contexte.banc.noeud(audio.ANTENNE.programme, "application.name")
	assert flux is not None
	contexte.banc.deplacer(flux, nom)
	time.sleep(CALME)


@then(parsers.re(r"(?:l'antenne|la sortie sans verrou) est reliée à « (?P<nom>[^»]+) »"))
def reliee(contexte: SimpleNamespace, nom: str) -> None:
	banc = contexte.banc
	assert banc._attendre(lambda: banc.reliee_a(contexte.programme) == {nom}), banc.reliee_a(contexte.programme)


@then("l'antenne n'est reliée à rien")
def reliee_a_rien(contexte: SimpleNamespace) -> None:
	time.sleep(CALME)
	assert contexte.banc.reliee_a(contexte.programme) == set()


@then("l'antenne joue toujours")
def joue_toujours(contexte: SimpleNamespace) -> None:
	"""Ni erreur, ni flux détruit : WirePlumber attend le périphérique, sans envoyer « defined target not found »."""
	(pipeline,) = contexte.pipelines
	bus = pipeline.get_bus()
	assert bus.pop_filtered(audio.Gst.MessageType.ERROR) is None
	assert contexte.banc.noeud(contexte.programme, "application.name") is not None


scenarios("sortie_verrouillee.feature")
