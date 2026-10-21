"""Fiche d'un marque-page de stream (https://github.com/dascritch/machincast/issues/34, spec § 8.13).

Un marque-page est une adresse de flux réutilisable, souvent en ligne par intermittence : plusieurs streams peuvent le
suivre, et jouent son adresse (machincast.lecture.diffusion). La fiche s'ouvre dans un onglet de la fenêtre
(machincast.interface.fenetre), depuis la liste des marques-pages, ou vide pour un nouveau marque-page.
Enregistrement, annulation et fermeture : machincast.interface.fiche.

- Le nom est obligatoire, propre au marque-page ; l'adresse est obligatoire. Les deux sont enregistrés sans les
  espaces qui les entourent. Une nouvelle adresse vaut pour tous les streams qui le suivent.
- Le test du flux (machincast.interface.essai_flux) porte sur l'adresse saisie, même pas encore enregistrée ; il
  s'arrête à la fermeture de la fiche.
- Les streams qui le suivent sont montrés ; ouvrir l'un d'eux ouvre sa fiche. Un marque-page qu'un stream suit ne se
  supprime pas (machincast.interface.suppression) : la base le refuserait aussi.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem, QWidget

from machincast.conformation import conformer
from machincast.horloge import Horloge
from machincast.interface.essai_flux import EssaiDeFlux, resultat_de_l_essai
from machincast.interface.fiche import Connexion, Fiche, Refus
from machincast.interface.ui.fiche_marque_page import Ui_FicheMarquePage

SONORE = Qt.ItemDataRole.UserRole
"""Rôle qui porte l'identifiant d'un stream, dans la liste des streams."""


class FicheMarquePage(Fiche):
	genre = "marque-page"

	def __init__(
		self, connexion: Connexion, identifiant: int | None, horloge: Horloge, parent: QWidget | None = None
	) -> None:
		super().__init__(connexion, identifiant, horloge, parent)
		self.ui = Ui_FicheMarquePage()
		self.ui.setupUi(self)
		self.brancher(self.ui.enregistrer, self.ui.annuler, self.ui.supprimer, self.ui.message)
		self._nom = ""
		self.essai = EssaiDeFlux(self)
		self.essai.termine.connect(self._essai_termine)
		self.ui.nom.textChanged.connect(self._modifier)
		self.ui.url.textChanged.connect(self._modifier)
		self.ui.tester.clicked.connect(self._tester)
		self.ui.streams.itemActivated.connect(self._ouvrir_stream)
		self.charger()

	def titre(self) -> str:
		if self.identifiant is None:
			return "Nouveau marque-page"
		return f"Marque-page : {self._nom}"

	def fermer(self) -> None:
		self.essai.arreter()

	def _lire(self) -> None:
		marque: tuple[object, ...] = ("", "")
		streams: list[tuple[object, ...]] = []
		with self.connexion.transaction():
			if self.identifiant is not None:
				ligne = self.connexion.execute(
					"SELECT nom, url FROM marques_pages_streams WHERE id = %s", (self.identifiant,)
				).fetchone()
				assert ligne is not None, f"marque-page {self.identifiant} absent"
				marque = ligne
				streams = self.connexion.execute(
					"SELECT id, COALESCE(titre, %s) FROM sonores WHERE marque_page_id = %s ORDER BY 2, id",
					(str(marque[1]), self.identifiant),
				).fetchall()
		nom, url = marque
		self._nom = str(nom)
		self.ui.nom.setText(self._nom)
		self.ui.url.setText(str(url))
		self.ui.streams.clear()
		for identifiant, titre in streams:
			item = QListWidgetItem(str(titre))
			item.setData(SONORE, int(str(identifiant)))
			self.ui.streams.addItem(item)

	def _ecrire(self) -> int:
		nom = conformer(self.ui.nom.text())
		url = self.ui.url.text().strip()
		if nom == "":
			raise Refus("Le nom est obligatoire.")
		pris = self.connexion.execute(
			"SELECT 1 FROM marques_pages_streams WHERE nom = %s AND id IS DISTINCT FROM %s", (nom, self.identifiant)
		).fetchone()
		if pris is not None:
			raise Refus(f"Un autre marque-page s'appelle déjà « {nom} ».")
		if url == "":
			raise Refus("L'adresse est obligatoire.")
		if self.identifiant is None:
			cree = self.connexion.execute(
				"INSERT INTO marques_pages_streams (nom, url) VALUES (%s, %s) RETURNING id", (nom, url)
			).fetchone()
			assert cree is not None
			return int(str(cree[0]))
		self.connexion.execute(
			"UPDATE marques_pages_streams SET nom = %s, url = %s WHERE id = %s", (nom, url, self.identifiant)
		)
		return self.identifiant

	def _tester(self) -> None:
		self.ui.tester.setEnabled(False)
		self.ui.resultat_essai.setText("Test du flux en cours…")
		self.essai.lancer(self.ui.url.text().strip())

	def _essai_termine(self, repond: bool, detail: str) -> None:
		self.ui.resultat_essai.setText(resultat_de_l_essai(repond, detail))
		self.ui.tester.setEnabled(True)

	def _ouvrir_stream(self, item: QListWidgetItem) -> None:
		self.ouverture_demandee.emit("sonore", int(item.data(SONORE)), item.text())
