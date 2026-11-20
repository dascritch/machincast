"""L'onglet « API » : les comptes de l'intranet et de l'API (https://github.com/dascritch/machincast/issues/537).

Il crée un compte, nom, mot de passe et rôle ; change son rôle et son mot de passe ; le désactive et le réactive ; le
supprime, après confirmation. Le mot de passe n'est jamais gardé, seulement son empreinte scrypt salée
(machincast.shared.passwords). Un nom se tape dans une adresse, https://nom@adresse : lettres sans accent, chiffres,
point, tiret et souligné.

Le compte se saisit dans la fenêtre ApiUserDialog, que les scénarios remplacent par ask_account.
"""

import logging
import re
from dataclasses import dataclass

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTreeWidgetItem, QWidget

from machincast.i18n import _
from machincast.interface import dialogs, display
from machincast.interface.columns import Columns
from machincast.interface.queries import api_users as queries
from machincast.interface.ui.api_tab import Ui_ApiScreen
from machincast.interface.ui.api_user import Ui_ApiUserDialog
from machincast.shared import passwords

log = logging.getLogger(__name__)

NAME = re.compile(r"[A-Za-z0-9._-]+")
"""Un nom de compte : ce que permet la contrainte de api_users.name."""
ROLE_NAMES = {"consult": _("consult"), "actions": _("API actions")}
"""Les rôles d'un compte, tels que l'onglet les nomme."""
ACTIVE = _("active")
DISABLED = _("disabled")
DISABLE = _("Disable")
ENABLE = _("Enable")
IDENTIFIER = Qt.ItemDataRole.UserRole
COLUMNS_VIEW = "api-utilisateurs"


@dataclass(frozen=True)
class Account:
	"""Ce qu'a saisi la fenêtre d'un compte."""

	name: str
	password: str
	role: str


def refusal(name: str, password: str, confirmation: str, *, taken: bool) -> str | None:
	"""Pourquoi la saisie d'un compte est refusée ; None si elle convient."""
	if name == "":
		return _("The name is required.")
	if NAME.fullmatch(name) is None:
		return _("The name only takes letters without accents, digits, dot, hyphen and underscore.")
	if taken:
		return _("Another user already has this name.")
	if not passwords.acceptable(password):
		return _("The password needs at least {count} characters.").format(count=passwords.MINIMUM_LENGTH)
	if password != confirmation:
		return _("The password and its confirmation differ.")
	return None


class ApiUserDialog(QDialog):
	"""La fenêtre d'un nouveau compte, ou du nouveau mot de passe d'un compte existant, nommé et sans rôle."""

	def __init__(self, parent: QWidget | None, connection: psycopg.Connection[TupleRow], name: str | None) -> None:
		super().__init__(parent)
		self.connection = connection
		self.ui = Ui_ApiUserDialog()
		self.ui.setupUi(self)
		for role in queries.ROLES:
			self.ui.role.addItem(ROLE_NAMES[role], role)
		self.existing = name is not None
		if name is not None:
			self.setWindowTitle(_("Password of {name}").format(name=name))
			self.ui.name.setText(name)
			self.ui.name.setReadOnly(True)
			self.ui.role.setVisible(False)
			self.ui.role_label.setVisible(False)
		self.ui.refusal.setVisible(False)
		ok = self.ui.buttons.button(QDialogButtonBox.StandardButton.Ok)
		ok.clicked.connect(self._check)
		self.ui.buttons.rejected.connect(self.reject)

	def account(self) -> Account:
		return Account(self.ui.name.text(), self.ui.password.text(), str(self.ui.role.currentData()))

	def _check(self) -> None:
		"""La saisie refusée reste ouverte, et dit pourquoi."""
		account = self.account()
		taken = False
		if not self.existing:
			with self.connection.transaction():
				taken = queries.name_taken(self.connection, account.name)
		reason = refusal(account.name, account.password, self.ui.confirmation.text(), taken=taken)
		if reason is not None:
			self.ui.refusal.setText(reason)
			self.ui.refusal.setVisible(True)
			return
		self.accept()


def ask_account(parent: QWidget, connection: psycopg.Connection[TupleRow], name: str | None) -> Account | None:
	"""Le compte saisi, ou le nouveau mot de passe du compte nommé ; None, la fenêtre annulée."""
	window = ApiUserDialog(parent, connection, name)
	if window.exec() != QDialog.DialogCode.Accepted:
		return None
	return window.account()


class ApiScreen(QWidget):
	"""La liste des comptes, et ce qui agit sur celui qui est choisi."""

	announces = Signal(str)
	"""Ce que vient de faire l'onglet, pour la barre d'état."""

	def __init__(self, connection: psycopg.Connection[TupleRow], parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.connection = connection
		self.ui = Ui_ApiScreen()
		self.ui.setupUi(self)
		for role in queries.ROLES:
			self.ui.role.addItem(ROLE_NAMES[role], role)
		self.columns = Columns(self.ui.users, COLUMNS_VIEW)
		self.ui.users.sortByColumn(0, Qt.SortOrder.AscendingOrder)
		self.ui.users.currentItemChanged.connect(self._follow)
		self.ui.new_user.clicked.connect(self.create_user)
		self.ui.change_password.clicked.connect(self.change_password)
		self.ui.disable.clicked.connect(self.toggle_disabled)
		self.ui.delete.clicked.connect(self.delete_user)
		self.ui.role.activated.connect(self._change_role)
		self.refresh()

	def refresh(self) -> None:
		"""Relit les comptes, en gardant celui qui était choisi ; une base injoignable laisse l'onglet tel quel."""
		chosen = self.chosen()
		try:
			with self.connection.transaction():
				found = queries.users(self.connection)
		except psycopg.Error as error:
			log.error(_("unreadable intranet users: {error}").format(error=error))
			return
		tree = self.ui.users
		tree.clear()
		for user in found:
			state = ACTIVE
			if user.disabled_at is not None:
				state = DISABLED
			line = QTreeWidgetItem([user.name, ROLE_NAMES[user.role], state, display.date(user.created_at)])
			line.setData(0, IDENTIFIER, user.identifier)
			line.setData(1, IDENTIFIER, user.role)
			line.setData(2, IDENTIFIER, user.disabled_at is not None)
			tree.addTopLevelItem(line)
			if user.identifier == chosen:
				tree.setCurrentItem(line)
		self._follow()

	def chosen(self) -> int | None:
		"""L'identifiant du compte choisi."""
		line = self.ui.users.currentItem()
		if line is None:
			return None
		identifier = line.data(0, IDENTIFIER)
		assert isinstance(identifier, int)
		return identifier

	def _chosen_name(self) -> str:
		line = self.ui.users.currentItem()
		assert line is not None
		return line.text(0)

	def _follow(self) -> None:
		"""Les actions sur un compte ne servent qu'un compte choisi ; « Désactiver » devient « Réactiver »."""
		line = self.ui.users.currentItem()
		for widget in (self.ui.role, self.ui.change_password, self.ui.disable, self.ui.delete):
			widget.setEnabled(line is not None)
		if line is None:
			return
		self.ui.role.setCurrentIndex(self.ui.role.findData(line.data(1, IDENTIFIER)))
		self.ui.disable.setText(DISABLE)
		if line.data(2, IDENTIFIER):
			self.ui.disable.setText(ENABLE)

	def _write(self, done: str) -> None:
		"""Relit l'onglet, et dit ce qui vient d'être fait."""
		self.refresh()
		self.announces.emit(done)

	def create_user(self) -> None:
		account = ask_account(self, self.connection, None)
		if account is None:
			return
		with self.connection.transaction():
			identifier = queries.create(self.connection, account.name, passwords.digest(account.password), account.role)
		self._write(_("User {name} created.").format(name=account.name))
		self._choose(identifier)

	def _choose(self, identifier: int) -> None:
		tree = self.ui.users
		for index in range(tree.topLevelItemCount()):
			line = tree.topLevelItem(index)
			if (line is not None) and (line.data(0, IDENTIFIER) == identifier):
				tree.setCurrentItem(line)

	def _change_role(self) -> None:
		identifier = self.chosen()
		if identifier is None:
			return
		role = str(self.ui.role.currentData())
		with self.connection.transaction():
			queries.set_role(self.connection, identifier, role)
		self._write(_("{name} now has the role {role}.").format(name=self._chosen_name(), role=ROLE_NAMES[role]))

	def change_password(self) -> None:
		identifier = self.chosen()
		if identifier is None:
			return
		name = self._chosen_name()
		account = ask_account(self, self.connection, name)
		if account is None:
			return
		with self.connection.transaction():
			queries.set_password(self.connection, identifier, passwords.digest(account.password))
		self._write(_("Password of {name} changed.").format(name=name))

	def toggle_disabled(self) -> None:
		line = self.ui.users.currentItem()
		identifier = self.chosen()
		if (line is None) or (identifier is None):
			return
		name = self._chosen_name()
		disabling = not line.data(2, IDENTIFIER)
		with self.connection.transaction():
			queries.set_disabled(self.connection, identifier, disabled=disabling)
		done = _("{name} enabled again.")
		if disabling:
			done = _("{name} disabled: it can no longer connect.")
		self._write(done.format(name=name))

	def delete_user(self) -> None:
		identifier = self.chosen()
		if identifier is None:
			return
		name = self._chosen_name()
		text = _(
			"Delete the intranet user {name}? It will no longer be able to connect, and its sessions will end."
		).format(name=name)
		if not dialogs.confirm_deletion(self, _("Delete a user"), text):
			return
		with self.connection.transaction():
			queries.delete(self.connection, identifier)
		self._write(_("User {name} deleted.").format(name=name))
