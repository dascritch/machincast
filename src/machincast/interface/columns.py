"""Colonnes des tableaux de l'interface (https://github.com/dascritch/machincast/issues/207).

Chaque tableau, QTableView ou QTreeView, est une vue, nommée par sa clé : « liste-sonores », « recherche »,
« fiche-banque-sonores »… Colonnes s'y attache, et :

- ajuste les colonnes à leur contenu (resizeColumnToContents) à chaque lecture du tableau : modèle remis à zéro,
  lignes ajoutées ou réordonnées. C'est un ajustement ponctuel, et non le mode ResizeToContents de Qt, qui ignore le
  contenu quand l'en-tête vertical est masqué, et interdit d'élargir une colonne à la main. Qt ne mesure que les
  lignes visibles du tableau : un tableau caché, dans un onglet pas encore ouvert, est ajusté quand il se montre ou
  change de taille. Une fois une colonne
  élargie à la main, l'ajustement s'arrête pour la vue, jusqu'à « Rétablir les colonnes » ;
- laisse déplacer une colonne en glissant son titre (setSectionsMovable) ;
- propose au clic droit sur les titres le menu des colonnes (menu) : une entrée à cocher par colonne, dans l'ordre
  affiché, la dernière colonne montrée restant inactive, puis « Rétablir les colonnes », qui remet l'ordre et les
  colonnes d'origine, oublie les largeurs et réajuste ;
- garde la disposition de la vue (QHeaderView.saveState : ordre, colonnes cachées, largeurs) dans les réglages du
  compte, fichier(), un fichier .ini hors du machincast.toml du poste : chacun garde ses vues. Une disposition gardée
  pour d'autres colonnes, d'une version précédente, est oubliée. L'indicateur de tri n'est pas repris : chaque vue
  garde le tri qu'elle a à l'ouverture ;
- propose au clic droit dans le tableau « Exporter ce tableau… » (https://github.com/dascritch/machincast/issues/329),
  après les entrées de sa ligne, s'il en a (line_menu) : un sélecteur de fichier (choose_file), puis le
  tableau tel qu'il est affiché, en CSV (in_csv) : les colonnes montrées, dans leur ordre, et les lignes que garde le
  filtre, dans l'ordre du tri. La barre d'état de la fenêtre dit où il est enregistré, ou pourquoi il ne l'est pas. Un
  export ne remplace jamais un fichier sonore (https://github.com/dascritch/machincast/issues/96).
"""

import csv
import io
import logging
import os
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QByteArray, QEvent, QModelIndex, QObject, QPoint, QSettings, Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
	QAbstractItemView,
	QFileDialog,
	QHeaderView,
	QMainWindow,
	QMenu,
	QTableView,
	QTreeView,
	QWidget,
)

from machincast.i18n import _
from machincast.protection import check_writing

log = logging.getLogger(__name__)

FILE: Path | None = None
"""Le fichier des réglages des vues ; None : celui du compte, sous $XDG_CONFIG_HOME. Les tests le remplacent."""
FILE_NAME = Path("machincast") / "vues.ini"
REINSTATE = _("Reset the columns")
PROPERTY = "vue"
"""Propriété de l'en-tête qui porte le nom de sa vue."""
EXPORT = _("Export this table…")
CSV_FILTER = _("CSV spreadsheet (*.csv)")
SEPARATOR = ";"
"""Séparateur du CSV, comme ceux de la diffusion et de l'airplay."""
ANNOUNCEMENT_DURATION = 10000
"""Millisecondes pendant lesquelles la barre d'état dit ce que l'export a donné."""


def choose_file(parent: QWidget, offers: str) -> Path | None:
	"""Le fichier où exporter le tableau, en .csv ; None si le choix est abandonné. Les tests le remplacent."""
	path, _filter = QFileDialog.getSaveFileName(parent, _("Export this table"), str(Path.home() / offers), CSV_FILTER)
	if path == "":
		return None
	return Path(path)


def file() -> Path:
	"""Les réglages des vues du compte : $XDG_CONFIG_HOME/machincast/vues.ini, ou ~/.config/machincast/vues.ini."""
	if FILE is not None:
		return FILE
	root = Path.home() / ".config"
	configuration = os.environ.get("XDG_CONFIG_HOME", "")
	if configuration != "":
		root = Path(configuration)
	return root / FILE_NAME


def settings() -> QSettings:
	return QSettings(str(file()), QSettings.Format.IniFormat)


def header(view: QAbstractItemView) -> QHeaderView:
	if isinstance(view, QTreeView):
		return view.header()
	assert isinstance(view, QTableView)
	return view.horizontalHeader()


class Columns(QObject):
	"""Les colonnes d'une vue : ajustées, déplaçables, à montrer ou cacher, gardées dans les réglages du compte."""

	def __init__(self, view: QAbstractItemView, name: str) -> None:
		super().__init__(view)
		self.view = view
		self.name = name
		self.header = header(view)
		self.adjusted_list = False
		"""Une colonne a été élargie à la main : l'ajustement au contenu s'arrête."""
		self._adjustment = False
		self._loading = False
		self._slides = False
		"""Le bouton de la souris est enfoncé sur les titres : un redimensionnement vient de l'utilisateur. Qt
		redimensionne aussi les colonnes de lui-même, en posant le tableau ou en étirant la dernière colonne."""
		self._adjust_soon = QTimer(self)
		self._adjust_soon.setSingleShot(True)
		self._adjust_soon.setInterval(0)
		self._adjust_soon.timeout.connect(self.adjust)
		self.line_menu: Callable[[QPoint], QMenu | None] | None = None
		self.before_export: Callable[[], None] | None = None
		"""Lit les lignes pas encore lues d'un tableau par pages, avant de l'exporter (https://github.com/dascritch/machincast/issues/383)."""
		"""Le menu de la ligne sous le clic droit, à la position du clic dans le tableau, que le tableau propose ;
		« Exporter ce tableau… » le complète."""
		view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		view.customContextMenuRequested.connect(self._show_table_menu)
		self.header.setProperty(PROPERTY, name)
		self.header.setSectionsMovable(True)
		self.header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.header.customContextMenuRequested.connect(self._show_menu)
		self._origin = QByteArray(self.header.saveState())
		self.restore()
		self.header.sectionMoved.connect(lambda *_: self.save())
		self.header.sectionResized.connect(self._resized)
		model = view.model()
		for signal in (model.modelReset, model.rowsInserted, model.layoutChanged):
			signal.connect(lambda *_: self._adjust_soon.start())
		view.installEventFilter(self)
		# Gardé ici : pendant la destruction du tableau, l'en-tête peut disparaître avant ses derniers événements.
		self._titles = self.header.viewport()
		self._titles.installEventFilter(self)
		self._adjust_soon.start()

	def eventFilter(self, object_: QObject, event: QEvent) -> bool:
		"""Un tableau qui se montre, ou change de taille, a de nouvelles lignes visibles à mesurer."""
		if object_ is self._titles:
			if event.type() == QEvent.Type.MouseButtonPress:
				self._slides = True
			elif event.type() == QEvent.Type.MouseButtonRelease:
				self._slides = False
			return False
		if event.type() in (QEvent.Type.Show, QEvent.Type.Resize):
			self._adjust_soon.start()
		return False

	def titles(self) -> list[str]:
		"""Les titres des colonnes, dans l'ordre du modèle."""
		model = self.view.model()
		return [str(model.headerData(column, Qt.Orientation.Horizontal)) for column in range(model.columnCount())]

	def shown_list(self) -> list[str]:
		"""Les titres des colonnes montrées, dans l'ordre affiché."""
		titles = self.titles()
		order = [self.header.logicalIndex(rank) for rank in range(self.header.count())]
		return [titles[column] for column in order if not self.header.isSectionHidden(column)]

	def adjust(self) -> None:
		"""Les colonnes à la largeur de leur contenu, tant qu'aucune n'a été élargie à la main."""
		if self.adjusted_list:
			return
		view = self.view
		assert isinstance(view, (QTableView, QTreeView))
		# Colonne par colonne : resizeColumnsToContents rétrécirait aussi la dernière, quand elle s'étire jusqu'au bord.
		self._adjustment = True
		try:
			for column in range(self.header.count()):
				view.resizeColumnToContents(column)
		finally:
			self._adjustment = False

	def display(self, column: int, visible: bool) -> None:
		self.header.setSectionHidden(column, not visible)
		self.save()

	def reinstate(self) -> None:
		"""L'ordre et les colonnes d'origine, les largeurs ajustées au contenu ; la disposition gardée est oubliée."""
		self._loading = True
		try:
			self.header.restoreState(self._origin)
		finally:
			self._loading = False
		self.adjusted_list = False
		settings().remove(self.name)
		self.adjust()

	def menu(self) -> QMenu:
		"""Le menu des colonnes : une entrée à cocher par colonne, dans l'ordre affiché, puis « Rétablir les
		colonnes »."""
		menu = QMenu(self.view)
		titles = self.titles()
		shown_list = len(self.shown_list())
		for rank in range(self.header.count()):
			column = self.header.logicalIndex(rank)
			action = QAction(titles[column], menu)
			action.setCheckable(True)
			visible = not self.header.isSectionHidden(column)
			action.setChecked(visible)
			# La dernière colonne montrée ne se cache pas : la vue resterait vide.
			action.setEnabled((not visible) or (shown_list > 1))
			action.toggled.connect(lambda ticked, column=column: self.display(column, ticked))
			menu.addAction(action)
		menu.addSeparator()
		menu.addAction(REINSTATE).triggered.connect(self.reinstate)
		return menu

	def _show_menu(self, position: QPoint) -> None:
		self.menu().popup(self.header.mapToGlobal(position))

	def table_menu(self, position: QPoint) -> QMenu:
		"""Le menu du clic droit à cette position du tableau : celui de sa ligne, s'il en a, puis « Exporter ce
		tableau… »."""
		menu = None
		if self.line_menu is not None:
			menu = self.line_menu(position)
		if menu is None:
			menu = QMenu(self.view)
		elif menu.actions() != []:
			menu.addSeparator()
		menu.addAction(EXPORT).triggered.connect(self.export)
		return menu

	def _show_table_menu(self, position: QPoint) -> None:
		menu = self.table_menu(position)
		menu.exec(self.view.viewport().mapToGlobal(position))
		menu.deleteLater()

	def in_csv(self) -> str:
		"""Le tableau tel qu'il est affiché : les titres et les cellules des colonnes montrées, dans l'ordre affiché,
		et les lignes montrées, dans l'ordre du tri ; seules les lignes de premier niveau d'un arbre."""
		model = self.view.model()
		# Un tableau lu par pages est exporté en entier (https://github.com/dascritch/machincast/issues/383).
		if self.before_export is not None:
			self.before_export()
		while model.canFetchMore(QModelIndex()):
			model.fetchMore(QModelIndex())
		titles = self.titles()
		order = [self.header.logicalIndex(rank) for rank in range(self.header.count())]
		columns = [column for column in order if not self.header.isSectionHidden(column)]
		output = io.StringIO()
		writer = csv.writer(output, delimiter=SEPARATOR, lineterminator="\n")
		writer.writerow([titles[column] for column in columns])
		for row in range(model.rowCount()):
			if (isinstance(self.view, QTableView)) and (self.view.isRowHidden(row)):
				continue
			cells = [model.index(row, column).data() for column in columns]
			writer.writerow([str((cell) or ("")) for cell in cells])
		return output.getvalue()

	def export(self) -> None:
		"""« Exporter ce tableau… » : le fichier choisi reçoit le tableau en CSV, en UTF-8 avec BOM pour les
		tableurs, avec l'extension .csv s'il ne l'a pas."""
		path = choose_file(self.view, f"{self.name}.csv")
		if path is None:
			return
		if path.suffix.lower() != ".csv":
			path = path.with_name(f"{path.name}.csv")
		try:
			check_writing(path)
			path.write_text(self.in_csv(), encoding="utf-8-sig", newline="")
		except OSError as error:
			log.error(_("export of table {name} impossible: {error}").format(name=self.name, error=error))
			self._announce(_("Export impossible: {error}").format(error=error))
			return
		self._announce(_("Table exported to {path}.").format(path=path))

	def _announce(self, text: str) -> None:
		window = self.view.window()
		if isinstance(window, QMainWindow):
			window.statusBar().showMessage(text, ANNOUNCEMENT_DURATION)

	def _resized(self, _column: int, _before: int, _after: int) -> None:
		if (self._adjustment) or (self._loading) or (not self._slides):
			return
		self.adjusted_list = True
		self.save()

	def save(self) -> None:
		if self._loading:
			return
		memory = settings()
		memory.beginGroup(self.name)
		memory.setValue("colonnes", self.titles())
		memory.setValue("disposition", self.header.saveState())
		memory.setValue("largeurs", self.adjusted_list)
		memory.endGroup()

	def restore(self) -> None:
		"""La disposition gardée, si elle est celle de ces colonnes ; le tri de la vue reste le sien."""
		memory = settings()
		memory.beginGroup(self.name)
		columns = memory.value("colonnes")
		arrangement = memory.value("disposition")
		widths = memory.value("largeurs")
		memory.endGroup()
		if (not isinstance(arrangement, QByteArray)) or (_list(columns) != self.titles()):
			return
		self._loading = True
		try:
			if not self.header.restoreState(arrangement):
				log.warning(_("unreadable column layout of view {name}: forgotten").format(name=self.name))
				return
		finally:
			self._loading = False
		self.adjusted_list = str(widths).lower() == "true"


def _list(value: object) -> list[str]:
	"""Une liste lue dans les réglages : QSettings rend une seule valeur, sans liste, pour une liste d'un élément."""
	if isinstance(value, list):
		return [str(item) for item in value]
	if value is None:
		return []
	return [str(value)]
