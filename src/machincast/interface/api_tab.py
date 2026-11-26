"""L'onglet « API » : les comptes de l'intranet et de l'API (https://github.com/dascritch/machincast/issues/537).

Il crée un compte, nom, mot de passe et rôle ; change son rôle et son mot de passe ; le désactive et le réactive ; le
supprime, après confirmation. Le mot de passe n'est jamais gardé, seulement son empreinte scrypt salée
(machincast.shared.passwords). Un nom se tape dans une adresse, https://nom@adresse : lettres sans accent, chiffres,
point, tiret et souligné.

Le compte se saisit dans la fenêtre ApiUserDialog, que les scénarios remplacent par ask_account.

Le second facteur (https://github.com/dascritch/machincast/issues/601) : l'onglet règle l'application d'authentification
d'un compte, une nouvelle clé montrée une seule fois avec son adresse otpauth:// (show_authenticator), ou la retire ; il
dit ses navigateurs connus, et les oublie : sa prochaine connexion repasse la première connexion.
"""

import logging
import re
from dataclasses import dataclass

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QMessageBox, QTreeWidgetItem, QWidget

from machincast.configuration import SESSION
from machincast.i18n import _, counted, ngettext, pgettext
from machincast.interface import dialogs, display
from machincast.interface.columns import Columns
from machincast.interface.queries import api_users as queries
from machincast.interface.ui.api_tab import Ui_ApiScreen
from machincast.interface.ui.api_user import Ui_ApiUserDialog
from machincast.shared import passwords, totp
from machincast.webserver import sessions

log = logging.getLogger(__name__)

NAME = re.compile(r"[A-Za-z0-9._-]+")
"""Un nom de compte : ce que permet la contrainte de api_users.name."""
ROLE_NAMES = {"consult": _("consult"), "actions": _("API actions")}
"""Les rôles d'un compte, tels que l'onglet les nomme."""
SESSION_STATES = {"pending": _("to validate"), "valid": _("valid"), "invalid": _("invalid")}
"""L'état d'une session (https://github.com/dascritch/machincast/issues/539)."""
ORIGINS = {"intranet": _("intranet"), "interface": _("desk")}
"""D'où vient une session : la mire de connexion, ou une génération au pupitre, pour l'API."""
SESSIONS_VIEW = "api-sessions"
ACTIVE = _("active")
DISABLED = _("disabled")
DISABLE = _("Disable")
ENABLE = pgettext("account", "Enable")
"""« Réactiver » un compte, quand « Activer » un sonore."""
IDENTIFIER = Qt.ItemDataRole.UserRole
COLUMNS_VIEW = "api-utilisateurs"
AUTHENTICATOR_SET = _("set")
"""L'application d'authentification d'un compte réglée ; display.EMPTY sinon."""
ISSUER = "MachinCast"


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


def show_token(parent: QWidget, name: str, value: str) -> None:
	"""Le jeton d'une session générée, montré une seule fois : la base n'en garde que l'empreinte."""
	window = QMessageBox(parent)
	window.setIcon(QMessageBox.Icon.Information)
	window.setWindowTitle(_("API session of {name}").format(name=name))
	window.setText(
		_(
			"Give this token to the tool that uses the API, in the header “Authorization: Bearer …”. It is shown only "
			"this once: MachinCast keeps only its fingerprint."
		)
	)
	window.setInformativeText(value)
	window.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
	window.exec()


def grouped(secret: str) -> str:
	"""La clé, en groupes de quatre caractères, plus facile à recopier."""
	groups = []
	for start in range(0, len(secret), 4):
		groups.append(secret[start : start + 4])
	return " ".join(groups)


def show_authenticator(parent: QWidget, name: str, secret: str, uri: str) -> bool:
	"""La nouvelle clé de l'application d'authentification du compte, montrée une seule fois, et son adresse
	otpauth:// : « Enregistrer » la garde, « Annuler » garde l'ancienne, s'il y en a une."""
	window = QMessageBox(parent)
	window.setIcon(QMessageBox.Icon.Information)
	window.setWindowTitle(_("Authentication app of {name}").format(name=name))
	window.setText(
		_(
			"Add this key to the authentication app of {name}, by hand or by the address below, then save it. It is "
			"shown only this once."
		).format(name=name)
	)
	window.setInformativeText(f"{grouped(secret)}\n\n{uri}")
	window.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
	window.setStandardButtons(QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel)
	return window.exec() == QMessageBox.StandardButton.Save


def ask_account(parent: QWidget, connection: psycopg.Connection[TupleRow], name: str | None) -> Account | None:
	"""Le compte saisi, ou le nouveau mot de passe du compte nommé ; None, la fenêtre annulée."""
	window = ApiUserDialog(parent, connection, name)
	if window.exec() != QDialog.DialogCode.Accepted:
		return None
	return window.account()


def ended_sessions(count: int) -> str:
	"""« 2 sessions terminées », après un message ; rien sans session terminée."""
	if count == 0:
		return ""
	return " " + counted("{count} session ended.", "{count} sessions ended.", count)


class ApiScreen(QWidget):
	"""La liste des comptes, et ce qui agit sur celui qui est choisi."""

	announces = Signal(str)
	"""Ce que vient de faire l'onglet, pour la barre d'état."""

	def __init__(
		self,
		connection: psycopg.Connection[TupleRow],
		session_hours: int = SESSION,
		parent: QWidget | None = None,
		*,
		issuer: str = ISSUER,
	) -> None:
		super().__init__(parent)
		self.connection = connection
		self.session_hours = session_hours
		self.issuer = issuer
		"""Le nom que l'application d'authentification donne à la clé : « MachinCast » et la radio."""
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
		self.session_columns = Columns(self.ui.sessions, SESSIONS_VIEW)
		self.ui.sessions.currentItemChanged.connect(self._follow_session)
		self.ui.new_session.clicked.connect(self.new_session)
		self.ui.invalidate_session.clicked.connect(self.invalidate_session)
		self.ui.authenticator.clicked.connect(self.set_up_authenticator)
		self.ui.remove_authenticator.clicked.connect(self.remove_authenticator)
		self.ui.forget_browsers.clicked.connect(self.forget_browsers)
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
			authenticator = display.EMPTY
			if user.authenticator:
				authenticator = AUTHENTICATOR_SET
			line = QTreeWidgetItem(
				[
					user.name,
					ROLE_NAMES[user.role],
					state,
					display.date(user.created_at),
					authenticator,
					str(user.browsers),
				]
			)
			line.setData(0, IDENTIFIER, user.identifier)
			line.setData(1, IDENTIFIER, user.role)
			line.setData(2, IDENTIFIER, user.disabled_at is not None)
			line.setData(4, IDENTIFIER, user.authenticator)
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
		ui = self.ui
		for widget in (
			ui.role,
			ui.change_password,
			ui.disable,
			ui.delete,
			ui.new_session,
			ui.authenticator,
			ui.forget_browsers,
		):
			widget.setEnabled(line is not None)
		ui.remove_authenticator.setEnabled((line is not None) and (bool(line.data(4, IDENTIFIER))))
		self.refresh_sessions()
		if line is None:
			return
		self.ui.role.setCurrentIndex(self.ui.role.findData(line.data(1, IDENTIFIER)))
		self.ui.disable.setText(DISABLE)
		if line.data(2, IDENTIFIER):
			self.ui.disable.setText(ENABLE)

	def refresh_sessions(self) -> None:
		"""Les sessions du compte choisi, la plus récente en tête (https://github.com/dascritch/machincast/issues/539)."""
		tree = self.ui.sessions
		tree.clear()
		identifier = self.chosen()
		if identifier is not None:
			with self.connection.transaction():
				found = queries.sessions_of(self.connection, identifier)
			for opened in found:
				limit = ""
				if opened.limit is not None:
					limit = display.date(opened.limit)
				line = QTreeWidgetItem(
					[
						SESSION_STATES[opened.state],
						ORIGINS[opened.origin],
						display.date(opened.created_at),
						limit,
						opened.address,
						opened.user_agent,
					]
				)
				line.setData(0, IDENTIFIER, opened.identifier)
				line.setData(1, IDENTIFIER, opened.state)
				tree.addTopLevelItem(line)
		self._follow_session()

	def _follow_session(self) -> None:
		"""« Invalider la session » ne sert qu'une session qui n'est pas déjà invalide."""
		line = self.ui.sessions.currentItem()
		self.ui.invalidate_session.setEnabled((line is not None) and (line.data(1, IDENTIFIER) != "invalid"))

	def new_session(self) -> None:
		"""Une session valide aussitôt, pour l'API ; son jeton, montré une fois."""
		identifier = self.chosen()
		if identifier is None:
			return
		name = self._chosen_name()
		value = sessions.token()
		with self.connection.transaction():
			queries.create_session(self.connection, identifier, sessions.fingerprint(value), self.session_hours)
		self.refresh_sessions()
		self.announces.emit(
			_("API session of {name} created, valid {hours} hours.").format(name=name, hours=self.session_hours)
		)
		show_token(self, name, value)

	def invalidate_session(self) -> None:
		line = self.ui.sessions.currentItem()
		if line is None:
			return
		session = line.data(0, IDENTIFIER)
		assert isinstance(session, int)
		with self.connection.transaction():
			queries.invalidate(self.connection, session)
		self.refresh_sessions()
		self.announces.emit(_("Session of {name} invalidated.").format(name=self._chosen_name()))

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
			ended = queries.set_password(self.connection, identifier, passwords.digest(account.password))
		self._write(_("Password of {name} changed.").format(name=name) + ended_sessions(ended))

	def toggle_disabled(self) -> None:
		line = self.ui.users.currentItem()
		identifier = self.chosen()
		if (line is None) or (identifier is None):
			return
		name = self._chosen_name()
		disabling = not line.data(2, IDENTIFIER)
		with self.connection.transaction():
			ended = queries.set_disabled(self.connection, identifier, disabled=disabling)
		done = _("{name} enabled again.")
		if disabling:
			done = _("{name} disabled: it can no longer connect.")
		self._write(done.format(name=name) + ended_sessions(ended))

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

	def set_up_authenticator(self) -> None:
		"""Une nouvelle clé pour l'application d'authentification du compte, gardée si la fenêtre l'enregistre
		(https://github.com/dascritch/machincast/issues/601)."""
		identifier = self.chosen()
		if identifier is None:
			return
		name = self._chosen_name()
		key = totp.secret()
		if not show_authenticator(self, name, key, totp.uri(self.issuer, name, key)):
			return
		with self.connection.transaction():
			queries.set_authenticator(self.connection, identifier, key)
		self._write(_("Authentication app of {name} set: it now gives its codes.").format(name=name))

	def remove_authenticator(self) -> None:
		identifier = self.chosen()
		if identifier is None:
			return
		name = self._chosen_name()
		with self.connection.transaction():
			queries.set_authenticator(self.connection, identifier, None)
		self._write(_("Authentication app of {name} removed.").format(name=name))

	def forget_browsers(self) -> None:
		"""Les navigateurs connus du compte, oubliés : sa prochaine connexion repasse la première connexion
		(https://github.com/dascritch/machincast/issues/601)."""
		identifier = self.chosen()
		if identifier is None:
			return
		name = self._chosen_name()
		with self.connection.transaction():
			count = queries.forget_browsers(self.connection, identifier)
		self._write(
			ngettext(
				"{count} browser of {name} forgotten: its next connection goes through the first connection again.",
				"{count} browsers of {name} forgotten: its next connection goes through the first connection again.",
				count,
			).format(count=count, name=name)
		)
