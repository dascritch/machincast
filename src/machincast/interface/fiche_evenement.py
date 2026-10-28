"""Fiche d'un événement (https://github.com/dascritch/machincast/issues/32, spec § 8.5).

La fiche s'ouvre dans un onglet de la fenêtre (machincast.interface.fenetre), depuis la liste des événements, ou vide
pour un nouvel événement. Enregistrement, annulation et fermeture : machincast.interface.fiche.

- Les noms sont enregistrés conformés (machincast.conformation, https://github.com/dascritch/machincast/issues/108) ; un
  nom public vide n'en est pas un (NULL). Deux événements n'ont pas le même nom interne.
- Le masquage « selon la séquence, la banque ou le sonore » (NULL) laisse décider le niveau suivant ; « masqués » et
  « affichés » l'imposent.
- Grille (spec § 3.1) : le début et la fin de la première occurrence, chacun à cocher, et les jours où elle revient.
  Sans début, ni fin ni jours : un fil musical sans début est permanent. Un événement de secours n'a ni dates ni
  jours : il ne joue qu'à la place d'un stream tombé. Une émission ou un spécial a un début ; une fin suit le début.
  Une date cochée part de l'heure de l'horloge, à la minute ; une fin, d'une heure après le début.
- Un événement ne chevauche pas un autre événement de même priorité (machincast.lecture.grille.chevauchement) ; une
  session sautée ne chevauche rien (https://github.com/dascritch/machincast/issues/273).
- Un événement de secours qu'un stream désigne reste de priorité secours : la base le refuserait aussi.
- La liste de lecture : sonores, banques et séquences (machincast.interface.elements). Un événement vide
  s'enregistre, pour être complété plus tard, avec un avertissement qui dit ce qu'en fait la diffusion selon sa
  priorité ; la liste des événements le montre en anomalie (https://github.com/dascritch/machincast/issues/140).
  L'avertissement d'une banque « ne pas répéter » appelée juste après elle-même suit la boucle de la
  liste : elle boucle, sauf pour une émission ou un spécial sans fin.
- Session sautée (https://github.com/dascritch/machincast/issues/295) : la prochaine session sautée de l'événement,
  en cours ou à venir (machincast.interface.sessions.prochaine_sautee), s'annonce en haut de la fiche, sous l'erreur,
  sur un liseret orange (session_sautee, LISERET_SESSION) : un avertissement, qui ne refuse rien. Le saut tient au
  jour : il suit l'heure de l'événement quand elle change. Son bouton « Rétablir » la rétablit, comme le clic droit du
  calendrier, sans toucher aux champs de la fiche ; il est inactif, avec une infobulle qui dit pourquoi, pour une
  session commencée, ou dont un événement de même priorité a pris la place. Rétablie, la session s'annonce
  (session_retablie) et Machin lecture relit la grille.
- Sa copie (https://github.com/dascritch/machincast/issues/130) garde sa priorité, ses noms, son masquage et sa liste
  de lecture, sans dates ni jours : son créneau est à choisir, une émission ou un spécial ne s'enregistrant pas sans
  début.
"""

from datetime import date, datetime, timedelta

from PySide6.QtCore import QDateTime, Signal
from PySide6.QtWidgets import QBoxLayout, QDateTimeEdit, QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from machincast.conformation import conformer
from machincast.horloge import Horloge
from machincast.interface import affichage
from machincast.interface.calendrier import date_longue, jour_et_mois
from machincast.interface.elements import Boutons, ListeElements
from machincast.interface.fiche import Connexion, Fiche, Refus
from machincast.interface.listes import EVENEMENT_VIDE
from machincast.interface.sessions import Session, chevauchee, commencee, prochaine_sautee, retablir
from machincast.interface.ui.fiche_evenement import Ui_FicheEvenement
from machincast.lecture.grille import JAMAIS, JOURS, Evenement, Priorite, chevauchement, lire_grille

PRIORITES: tuple[tuple[str, str], ...] = (
	("secours", "Secours"),
	("fil_musical", "Fil musical"),
	("emission", "Émission"),
	("special", "Spécial"),
)
"""Valeurs de evenements.priorite, dans l'ordre du choix de la fiche : de la plus basse à la plus haute, comme le type
priorite_evenement (https://github.com/dascritch/machincast/issues/253)."""
NOUVELLE = "emission"
"""Priorité d'un nouvel événement."""
SANS_FIN_NE_BOUCLE_PAS = ("emission", "special")
"""Priorités dont la liste ne boucle pas, sans fin : l'occurrence se termine au bout de sa liste."""
MASQUAGES: tuple[tuple[bool | None, str], ...] = (
	(None, "Selon la séquence, la banque ou le sonore"),
	(True, "Masqués"),
	(False, "Affichés"),
)
"""Valeurs de evenements.masquer_metadonnees, dans l'ordre du choix de la fiche."""
REPETITION = "Un sonore, une banque ou une séquence peut revenir plusieurs fois dans un événement."
"""Remarque des choix d'éléments."""
DUREE_PAR_DEFAUT = timedelta(hours=1)
"""Écart entre le début et une fin qui se coche."""
ORANGE = "#ef6c00"
"""Orange du liseret d'une session sautée : un avertissement, lisible sur un fond clair comme sur un fond sombre."""
LISERET_SESSION = f"QFrame#session_sautee {{ border: 4px solid {ORANGE}; }}"
RETABLIR = "Rétablir"
COMMENCEE = "Elle a déjà commencé : elle ne se rétablit plus."


def _montrer(date: QDateTimeEdit, instant: datetime) -> None:
	date.setDateTime(QDateTime.fromSecsSinceEpoch(int(instant.timestamp())))


class FicheEvenement(Fiche):
	genre = "événement"
	session_retablie = Signal(str)
	"""Une session sautée a été rétablie depuis la fiche : ce que la barre d'état en annonce. Machin lecture doit
	relire la grille (https://github.com/dascritch/machincast/issues/295)."""

	def __init__(
		self, connexion: Connexion, identifiant: int | None, horloge: Horloge, parent: QWidget | None = None
	) -> None:
		super().__init__(connexion, identifiant, horloge, parent)
		self.ui = Ui_FicheEvenement()
		self.ui.setupUi(self)
		ui = self.ui
		self.brancher(ui.enregistrer, ui.annuler, ui.supprimer, ui.message, ui.dupliquer)
		self._construire_l_annonce_de_session()
		for _valeur, texte in PRIORITES:
			ui.priorite.addItem(texte)
		for _masque, texte in MASQUAGES:
			ui.masquage.addItem(texte)
		self.jours = [getattr(ui, jour) for jour in JOURS]
		self._nom = ""
		boutons = Boutons(
			{
				"sonore": ui.ajouter_sonores,
				"banque": ui.ajouter_banques,
				"séquence": ui.ajouter_sequences,
				"feed": ui.ajouter_feeds,
			},
			ui.retirer_element,
			ui.monter,
			ui.descendre,
		)
		self.elements = ListeElements(self, ui.elements, boutons, "evenements_elements", "evenement_id", REPETITION)
		self.elements.changee.connect(self._modifier)
		self.elements.changee.connect(self._avertir)
		ui.nom_interne.textChanged.connect(self._modifier)
		ui.nom_public.textChanged.connect(self._modifier)
		ui.masquage.currentIndexChanged.connect(self._modifier)
		ui.priorite.currentIndexChanged.connect(self._grille)
		ui.priorite.currentIndexChanged.connect(self._modifier)
		ui.priorite.currentIndexChanged.connect(self._avertir)
		ui.a_debut.toggled.connect(self._grille)
		ui.a_debut.toggled.connect(self._modifier)
		ui.a_fin.toggled.connect(self._cocher_fin)
		ui.a_fin.toggled.connect(self._grille)
		ui.a_fin.toggled.connect(self._modifier)
		ui.a_fin.toggled.connect(self._avertir)
		for champ in (ui.debut, ui.fin):
			champ.dateTimeChanged.connect(self._modifier)
		for jour in self.jours:
			jour.toggled.connect(self._modifier)
		self.charger()

	def titre(self) -> str:
		if self.est_une_copie():
			return f"Nouvel événement, copie de {self._nom}"
		if self.identifiant is None:
			return "Nouvel événement"
		return f"Événement : {self._nom}"

	def _priorite(self) -> str:
		return PRIORITES[self.ui.priorite.currentIndex()][0]

	def _lire(self) -> None:
		"""Lit l'événement en base, ou celui qu'il copie, sans ses dates ni ses jours ; un nouvel événement est une
		émission, sans dates, au masquage hérité."""
		evenement: tuple[object, ...] = ("", None, NOUVELLE, None, None, [], None)
		lu = self.lu()
		with self.connexion.transaction():
			if lu is not None:
				ligne = self.connexion.execute(
					"SELECT nom_interne, nom_public, priorite::text, debut, fin, jours_recurrence::text[],"
					" masquer_metadonnees FROM evenements WHERE id = %s",
					(lu,),
				).fetchone()
				assert ligne is not None, f"événement {lu} absent"
				evenement = ligne
			self.elements.charger(lu, self.est_une_copie())
		nom, nom_public, priorite, debut, fin, jours, masquage = evenement
		if self.est_une_copie():
			debut, fin, jours = None, None, []
		ui = self.ui
		self._nom = str(nom)
		ui.nom_interne.setText(self._nom)
		if self.est_une_copie():
			ui.nom_interne.setText(self.nom_de_la_copie(self._nom))
		ui.nom_public.setText(str((nom_public) or ("")))
		ui.priorite.setCurrentIndex(next(i for i, (valeur, _texte) in enumerate(PRIORITES) if valeur == priorite))
		ui.masquage.setCurrentIndex(next(i for i, (valeur, _texte) in enumerate(MASQUAGES) if valeur is masquage))
		maintenant = self.horloge.maintenant().replace(second=0, microsecond=0)
		depart = maintenant
		if isinstance(debut, datetime):
			depart = debut
		# Une fin qui se coche part d'une heure après le début (_cocher_fin).
		arrivee = depart
		if isinstance(fin, datetime):
			arrivee = fin
		_montrer(ui.debut, depart)
		_montrer(ui.fin, arrivee)
		# Chaque case met la grille à jour quand elle change d'état (toggled) : le début d'abord, qui permet le reste.
		ui.a_debut.setChecked(isinstance(debut, datetime))
		ui.a_fin.setChecked(isinstance(fin, datetime))
		coches = set()
		if isinstance(jours, list):
			coches = {str(jour) for jour in jours}
		for nom_du_jour, jour in zip(JOURS, self.jours, strict=True):
			jour.setChecked(nom_du_jour in coches)
		# Une priorité déjà choisie ne change pas l'index : l'avertissement ne suit pas de lui-même.
		self._grille()
		self._avertir()
		self._annoncer_la_session()

	# ─── Session sautée (https://github.com/dascritch/machincast/issues/295) ───

	def _construire_l_annonce_de_session(self) -> None:
		"""L'annonce, sous l'erreur de la fiche, cachée sans session sautée."""
		self.session_sautee = QFrame(self)
		self.session_sautee.setObjectName("session_sautee")
		self.session_sautee.setStyleSheet(LISERET_SESSION)
		self.session_sautee.setAccessibleName("Session sautée")
		self.texte_de_session = QLabel(self.session_sautee)
		self.texte_de_session.setWordWrap(True)
		self.retablir_la_session = QPushButton(RETABLIR, self.session_sautee)
		self.retablir_la_session.clicked.connect(self._retablir_la_session)
		ligne = QHBoxLayout(self.session_sautee)
		ligne.setContentsMargins(10, 6, 6, 6)
		ligne.addWidget(self.texte_de_session, 1)
		ligne.addWidget(self.retablir_la_session)
		self.session_sautee.hide()
		disposition = self.layout()
		assert isinstance(disposition, QBoxLayout)
		disposition.insertWidget(disposition.indexOf(self.erreur) + 1, self.session_sautee)
		self._session: Session | None = None

	def _prochaine_sautee(self) -> Session | None:
		"""Celle de l'événement en base ; aucune pour une fiche nouvelle, une copie ou un événement supprimé."""
		if (self.identifiant is None) or (self.est_une_copie()):
			return None
		evenement = next((lu for lu in lire_grille(self.connexion) if lu.id == self.identifiant), None)
		if evenement is None:
			return None
		return prochaine_sautee(evenement, self.horloge.maintenant())

	def _annoncer_la_session(self) -> None:
		"""Montre la prochaine session sautée, et si elle se rétablit ; cache l'annonce sans session sautée."""
		maintenant = self.horloge.maintenant()
		empechement = None
		with self.connexion.transaction():
			self._session = self._prochaine_sautee()
			if self._session is not None:
				empechement = self._empechement(self._session, maintenant)
		session = self._session
		if session is None:
			self.session_sautee.hide()
			return
		jouera = "ne joue pas" if commencee(session, maintenant) else "ne jouera pas"
		self.texte_de_session.setText(
			f"La session du {date_longue(session.debut.date())} à {session.debut:%H:%M} est sautée : elle {jouera}."
		)
		self.retablir_la_session.setEnabled(empechement is None)
		self.retablir_la_session.setToolTip(
			(empechement) or ("Rétablir la session : elle jouera de nouveau, sans toucher aux champs de la fiche.")
		)
		self.session_sautee.show()

	def _empechement(self, session: Session, maintenant: datetime) -> str | None:
		"""Pourquoi la session ne se rétablit pas, comme au calendrier ; None si elle le peut. Dans une transaction."""
		if commencee(session, maintenant):
			return COMMENCEE
		trouve = chevauchee(self.connexion, session, maintenant)
		if trouve is None:
			return None
		autre, instant = trouve
		return (
			f"« {autre.nom} », de même priorité, a pris sa place le {jour_et_mois(instant.date())} à {instant:%H:%M}."
		)

	def _retablir_la_session(self) -> None:
		"""Rétablit la session annoncée, relue en base, sans toucher aux champs de la fiche ; ce qui l'empêche, apparu
		depuis l'annonce, s'affiche en erreur."""
		maintenant = self.horloge.maintenant()
		with self.connexion.transaction():
			session = self._prochaine_sautee()
			if session is None:
				empechement = None
			else:
				empechement = self._empechement(session, maintenant)
				if empechement is None:
					retablir(self.connexion, session)
		self._annoncer_la_session()
		if session is None:
			return
		if empechement is not None:
			self.signaler_l_erreur(f"Session non rétablie : {empechement}")
			return
		nom, jour = session.evenement.nom, session.debut.date()
		self.session_retablie.emit(f"Session de « {nom} » du {jour_et_mois(jour)} à {session.debut:%H:%M} rétablie.")

	def prevoir(self, debut: datetime, fin: datetime) -> None:
		"""Les dates d'un nouvel événement demandé depuis le calendrier
		(https://github.com/dascritch/machincast/issues/36) : la fiche est modifiée, rien n'est enregistré avant
		« Enregistrer »."""
		ui = self.ui
		_montrer(ui.debut, debut.astimezone())
		_montrer(ui.fin, fin.astimezone())
		ui.a_debut.setChecked(True)
		# Cocher les dates modifie la fiche (_modifier).
		ui.a_fin.setChecked(True)

	def _grille(self) -> None:
		"""Ce qui se saisit de la grille : rien pour un événement de secours ; ni fin ni jours sans début."""
		ui = self.ui
		secours = self._priorite() == "secours"
		if secours:
			ui.a_debut.setChecked(False)
		avec_debut = ui.a_debut.isChecked()
		if not avec_debut:
			ui.a_fin.setChecked(False)
			for jour in self.jours:
				jour.setChecked(False)
		ui.a_debut.setEnabled(not secours)
		ui.debut.setEnabled(avec_debut)
		ui.a_fin.setEnabled(avec_debut)
		ui.fin.setEnabled(ui.a_fin.isChecked())
		for jour in self.jours:
			jour.setEnabled(avec_debut)

	def _cocher_fin(self) -> None:
		"""Une fin cochée qui ne suit pas le début part d'une heure après lui."""
		ui = self.ui
		if ui.fin.dateTime() <= ui.debut.dateTime():
			ui.fin.setDateTime(ui.debut.dateTime().addSecs(int(DUREE_PAR_DEFAUT.total_seconds())))

	def _avertir(self) -> None:
		"""Un événement vide, selon sa priorité, ou une banque « ne pas répéter » appelée juste après elle-même : cet
		appel sera sauté. La liste boucle, sauf pour une émission ou un spécial sans fin."""
		boucle = (self._priorite() not in SANS_FIN_NE_BOUCLE_PAS) or (self.ui.a_fin.isChecked())
		avertissements = self.elements.avertissements(boucle)
		if self.elements.lignes() == []:
			avertissements = [EVENEMENT_VIDE[self._priorite()]]
		self.ui.avertissement.setText("\n".join(avertissements))

	def _ecrire(self) -> int:
		ui = self.ui
		nom = conformer(ui.nom_interne.text())
		if nom == "":
			raise Refus("Le nom interne est obligatoire.", ui.nom_interne)
		pris = self.connexion.execute(
			"SELECT 1 FROM evenements WHERE nom_interne = %s AND id IS DISTINCT FROM %s AND supprime_le IS NULL",
			(nom, self.identifiant),
		).fetchone()
		if pris is not None:
			raise Refus(f"Un autre événement s'appelle déjà « {nom} ».", ui.nom_interne)
		priorite = self._priorite()
		debut, fin = affichage.date_cochee(ui.a_debut, ui.debut), affichage.date_cochee(ui.a_fin, ui.fin)
		if (priorite in SANS_FIN_NE_BOUCLE_PAS) and (debut is None):
			raise Refus("Une émission ou un spécial a un début.", ui.priorite, ui.a_debut)
		if (debut is not None) and (fin is not None) and (fin <= debut):
			raise Refus("La fin doit suivre le début.", ui.a_debut, ui.a_fin)
		jours = [nom_du_jour for nom_du_jour, jour in zip(JOURS, self.jours, strict=True) if jour.isChecked()]
		self._refuser_chevauchement(nom, priorite, debut, fin, jours)
		self._refuser_secours_designe(priorite)
		valeurs = (
			nom,
			(conformer(ui.nom_public.text())) or (None),
			priorite,
			debut,
			fin,
			jours,
			MASQUAGES[ui.masquage.currentIndex()][0],
		)
		if self.identifiant is None:
			creee = self.connexion.execute(
				"INSERT INTO evenements"
				" (nom_interne, nom_public, priorite, debut, fin, jours_recurrence, masquer_metadonnees)"
				" VALUES (%s, %s, %s, %s, %s, %s::jour_semaine[], %s) RETURNING id",
				valeurs,
			).fetchone()
			assert creee is not None
			identifiant = int(str(creee[0]))
		else:
			identifiant = self.identifiant
			self.connexion.execute(
				"UPDATE evenements SET nom_interne = %s, nom_public = %s, priorite = %s, debut = %s, fin = %s,"
				" jours_recurrence = %s::jour_semaine[], masquer_metadonnees = %s WHERE id = %s",
				(*valeurs, identifiant),
			)
		self.elements.ecrire(identifiant)
		return identifiant

	def _refuser_chevauchement(
		self, nom: str, priorite: str, debut: datetime | None, fin: datetime | None, jours: list[str]
	) -> None:
		place = Evenement(
			id=-1,
			nom=nom,
			priorite=Priorite(priorite),
			debut=debut,
			fin=fin,
			jours=frozenset(JOURS.index(jour) for jour in jours),
			modifie_le=JAMAIS,
			sautees=self._sautees(),
		)
		autres = [autre for autre in lire_grille(self.connexion) if autre.id != self.identifiant]
		trouve = chevauchement(place, autres, depuis=self.horloge.maintenant())
		if trouve is not None:
			autre, instant = trouve
			raise Refus(
				f"Chevauche l'événement « {autre.nom} », de même priorité, le {instant:%d/%m/%Y à %H:%M}.",
				self.ui.priorite,
				self.ui.a_debut,
				self.ui.a_fin,
			)

	def _sautees(self) -> frozenset[date]:
		"""Les jours de ses sessions sautées, qui ne chevauchent rien (https://github.com/dascritch/machincast/issues/273)."""
		if self.identifiant is None:
			return frozenset()
		lignes = self.connexion.execute(
			"SELECT jour FROM evenements_sauts WHERE evenement_id = %s", (self.identifiant,)
		).fetchall()
		return frozenset(jour for (jour,) in lignes if isinstance(jour, date))

	def _refuser_secours_designe(self, priorite: str) -> None:
		"""Un événement de secours qu'un stream désigne garde sa priorité."""
		if (self.identifiant is None) or (priorite == "secours"):
			return
		streams = self.connexion.execute(
			"SELECT COALESCE(titre, url_stream) FROM sonores WHERE secours_evenement_id = %s ORDER BY 1",
			(self.identifiant,),
		).fetchall()
		if streams != []:
			noms = ", ".join(f"« {stream} »" for (stream,) in streams)
			raise Refus(
				f"Des streams ont cet événement pour secours : {noms}. Il reste de priorité « Secours ».",
				self.ui.priorite,
			)
