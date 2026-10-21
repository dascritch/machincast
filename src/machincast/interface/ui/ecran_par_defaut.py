# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ecran_par_defaut.ui'
##
## Created by: Qt User Interface Compiler version 6.10.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QFormLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QProgressBar, QSizePolicy, QTableView, QToolButton,
    QVBoxLayout, QWidget)

class Ui_EcranParDefaut(object):
    def setupUi(self, EcranParDefaut):
        if not EcranParDefaut.objectName():
            EcranParDefaut.setObjectName(u"EcranParDefaut")
        EcranParDefaut.resize(1100, 760)
        self.disposition = QVBoxLayout(EcranParDefaut)
        self.disposition.setObjectName(u"disposition")
        self.bandeau = QHBoxLayout()
        self.bandeau.setObjectName(u"bandeau")
        self.heure = QLabel(EcranParDefaut)
        self.heure.setObjectName(u"heure")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.heure.setFont(font)
        self.heure.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.bandeau.addWidget(self.heure)

        self.texte_public = QLabel(EcranParDefaut)
        self.texte_public.setObjectName(u"texte_public")
        font1 = QFont()
        font1.setPointSize(12)
        font1.setItalic(True)
        self.texte_public.setFont(font1)
        self.texte_public.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.texte_public.setWordWrap(True)
        self.texte_public.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.bandeau.addWidget(self.texte_public)

        self.etat_lecture = QLabel(EcranParDefaut)
        self.etat_lecture.setObjectName(u"etat_lecture")
        font2 = QFont()
        font2.setPointSize(12)
        font2.setBold(True)
        self.etat_lecture.setFont(font2)
        self.etat_lecture.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.bandeau.addWidget(self.etat_lecture)

        self.bandeau.setStretch(1, 1)

        self.disposition.addLayout(self.bandeau)

        self.ligne_evenement_antenne = QHBoxLayout()
        self.ligne_evenement_antenne.setObjectName(u"ligne_evenement_antenne")
        self.evenement_antenne = QLabel(EcranParDefaut)
        self.evenement_antenne.setObjectName(u"evenement_antenne")
        self.evenement_antenne.setFont(font2)
        self.evenement_antenne.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.evenement_antenne.setWordWrap(True)

        self.ligne_evenement_antenne.addWidget(self.evenement_antenne)

        self.ligne_evenement_antenne.setStretch(0, 1)

        self.disposition.addLayout(self.ligne_evenement_antenne)

        self.sonores = QHBoxLayout()
        self.sonores.setObjectName(u"sonores")
        self.cadre_en_cours = QGroupBox(EcranParDefaut)
        self.cadre_en_cours.setObjectName(u"cadre_en_cours")
        self.disposition_en_cours = QVBoxLayout(self.cadre_en_cours)
        self.disposition_en_cours.setObjectName(u"disposition_en_cours")
        self.ligne_en_cours_titre = QHBoxLayout()
        self.ligne_en_cours_titre.setObjectName(u"ligne_en_cours_titre")
        self.en_cours_titre = QLabel(self.cadre_en_cours)
        self.en_cours_titre.setObjectName(u"en_cours_titre")
        font3 = QFont()
        font3.setPointSize(14)
        font3.setBold(True)
        self.en_cours_titre.setFont(font3)
        self.en_cours_titre.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.en_cours_titre.setWordWrap(True)

        self.ligne_en_cours_titre.addWidget(self.en_cours_titre)

        self.ouvrir_sonore_en_cours = QToolButton(self.cadre_en_cours)
        self.ouvrir_sonore_en_cours.setObjectName(u"ouvrir_sonore_en_cours")
        self.ouvrir_sonore_en_cours.setEnabled(False)

        self.ligne_en_cours_titre.addWidget(self.ouvrir_sonore_en_cours)

        self.ligne_en_cours_titre.setStretch(0, 1)

        self.disposition_en_cours.addLayout(self.ligne_en_cours_titre)

        self.formulaire_en_cours = QFormLayout()
        self.formulaire_en_cours.setObjectName(u"formulaire_en_cours")
        self.intitule_en_cours_evenement = QLabel(self.cadre_en_cours)
        self.intitule_en_cours_evenement.setObjectName(u"intitule_en_cours_evenement")

        self.formulaire_en_cours.setWidget(0, QFormLayout.ItemRole.LabelRole, self.intitule_en_cours_evenement)

        self.ligne_en_cours_evenement = QHBoxLayout()
        self.ligne_en_cours_evenement.setObjectName(u"ligne_en_cours_evenement")
        self.en_cours_evenement = QLabel(self.cadre_en_cours)
        self.en_cours_evenement.setObjectName(u"en_cours_evenement")
        self.en_cours_evenement.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.en_cours_evenement.setWordWrap(True)

        self.ligne_en_cours_evenement.addWidget(self.en_cours_evenement)

        self.ouvrir_evenement_en_cours = QToolButton(self.cadre_en_cours)
        self.ouvrir_evenement_en_cours.setObjectName(u"ouvrir_evenement_en_cours")
        self.ouvrir_evenement_en_cours.setEnabled(False)

        self.ligne_en_cours_evenement.addWidget(self.ouvrir_evenement_en_cours)

        self.ligne_en_cours_evenement.setStretch(0, 1)

        self.formulaire_en_cours.setLayout(0, QFormLayout.ItemRole.FieldRole, self.ligne_en_cours_evenement)

        self.intitule_en_cours_sequence = QLabel(self.cadre_en_cours)
        self.intitule_en_cours_sequence.setObjectName(u"intitule_en_cours_sequence")

        self.formulaire_en_cours.setWidget(1, QFormLayout.ItemRole.LabelRole, self.intitule_en_cours_sequence)

        self.ligne_en_cours_sequence = QHBoxLayout()
        self.ligne_en_cours_sequence.setObjectName(u"ligne_en_cours_sequence")
        self.en_cours_sequence = QLabel(self.cadre_en_cours)
        self.en_cours_sequence.setObjectName(u"en_cours_sequence")
        self.en_cours_sequence.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.en_cours_sequence.setWordWrap(True)

        self.ligne_en_cours_sequence.addWidget(self.en_cours_sequence)

        self.ouvrir_sequence_en_cours = QToolButton(self.cadre_en_cours)
        self.ouvrir_sequence_en_cours.setObjectName(u"ouvrir_sequence_en_cours")
        self.ouvrir_sequence_en_cours.setEnabled(False)

        self.ligne_en_cours_sequence.addWidget(self.ouvrir_sequence_en_cours)

        self.ligne_en_cours_sequence.setStretch(0, 1)

        self.formulaire_en_cours.setLayout(1, QFormLayout.ItemRole.FieldRole, self.ligne_en_cours_sequence)

        self.intitule_en_cours_banque = QLabel(self.cadre_en_cours)
        self.intitule_en_cours_banque.setObjectName(u"intitule_en_cours_banque")

        self.formulaire_en_cours.setWidget(2, QFormLayout.ItemRole.LabelRole, self.intitule_en_cours_banque)

        self.ligne_en_cours_banque = QHBoxLayout()
        self.ligne_en_cours_banque.setObjectName(u"ligne_en_cours_banque")
        self.en_cours_banque = QLabel(self.cadre_en_cours)
        self.en_cours_banque.setObjectName(u"en_cours_banque")
        self.en_cours_banque.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.en_cours_banque.setWordWrap(True)

        self.ligne_en_cours_banque.addWidget(self.en_cours_banque)

        self.ouvrir_banque_en_cours = QToolButton(self.cadre_en_cours)
        self.ouvrir_banque_en_cours.setObjectName(u"ouvrir_banque_en_cours")
        self.ouvrir_banque_en_cours.setEnabled(False)

        self.ligne_en_cours_banque.addWidget(self.ouvrir_banque_en_cours)

        self.ligne_en_cours_banque.setStretch(0, 1)

        self.formulaire_en_cours.setLayout(2, QFormLayout.ItemRole.FieldRole, self.ligne_en_cours_banque)

        self.intitule_en_cours_horaire = QLabel(self.cadre_en_cours)
        self.intitule_en_cours_horaire.setObjectName(u"intitule_en_cours_horaire")

        self.formulaire_en_cours.setWidget(3, QFormLayout.ItemRole.LabelRole, self.intitule_en_cours_horaire)

        self.en_cours_horaire = QLabel(self.cadre_en_cours)
        self.en_cours_horaire.setObjectName(u"en_cours_horaire")
        self.en_cours_horaire.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.en_cours_horaire.setWordWrap(True)

        self.formulaire_en_cours.setWidget(3, QFormLayout.ItemRole.FieldRole, self.en_cours_horaire)

        self.intitule_en_cours_emplacement = QLabel(self.cadre_en_cours)
        self.intitule_en_cours_emplacement.setObjectName(u"intitule_en_cours_emplacement")

        self.formulaire_en_cours.setWidget(4, QFormLayout.ItemRole.LabelRole, self.intitule_en_cours_emplacement)

        self.en_cours_emplacement = QLineEdit(self.cadre_en_cours)
        self.en_cours_emplacement.setObjectName(u"en_cours_emplacement")
        self.en_cours_emplacement.setFrame(False)
        self.en_cours_emplacement.setReadOnly(True)

        self.formulaire_en_cours.setWidget(4, QFormLayout.ItemRole.FieldRole, self.en_cours_emplacement)


        self.disposition_en_cours.addLayout(self.formulaire_en_cours)

        self.en_cours_progression = QProgressBar(self.cadre_en_cours)
        self.en_cours_progression.setObjectName(u"en_cours_progression")
        self.en_cours_progression.setMaximum(100)
        self.en_cours_progression.setValue(0)

        self.disposition_en_cours.addWidget(self.en_cours_progression)


        self.sonores.addWidget(self.cadre_en_cours)

        self.colonne_antenne = QGroupBox(EcranParDefaut)
        self.colonne_antenne.setObjectName(u"colonne_antenne")
        self.colonne_antenne.setMaximumSize(QSize(140, 16777215))
        self.disposition_antenne = QVBoxLayout(self.colonne_antenne)
        self.disposition_antenne.setObjectName(u"disposition_antenne")
        self.voyant_saturation = QLabel(self.colonne_antenne)
        self.voyant_saturation.setObjectName(u"voyant_saturation")
        font4 = QFont()
        font4.setPointSize(7)
        self.voyant_saturation.setFont(font4)
        self.voyant_saturation.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.disposition_antenne.addWidget(self.voyant_saturation)

        self.place_vumetre = QWidget(self.colonne_antenne)
        self.place_vumetre.setObjectName(u"place_vumetre")
        self.place_vumetre.setMinimumSize(QSize(90, 160))

        self.disposition_antenne.addWidget(self.place_vumetre)

        self.voyant_silence = QLabel(self.colonne_antenne)
        self.voyant_silence.setObjectName(u"voyant_silence")
        self.voyant_silence.setFont(font4)
        self.voyant_silence.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.disposition_antenne.addWidget(self.voyant_silence)

        self.etat_moniteur = QLabel(self.colonne_antenne)
        self.etat_moniteur.setObjectName(u"etat_moniteur")
        self.etat_moniteur.setWordWrap(True)

        self.disposition_antenne.addWidget(self.etat_moniteur)


        self.sonores.addWidget(self.colonne_antenne)

        self.cadre_prochain = QGroupBox(EcranParDefaut)
        self.cadre_prochain.setObjectName(u"cadre_prochain")
        self.disposition_prochain = QVBoxLayout(self.cadre_prochain)
        self.disposition_prochain.setObjectName(u"disposition_prochain")
        self.ligne_prochain_titre = QHBoxLayout()
        self.ligne_prochain_titre.setObjectName(u"ligne_prochain_titre")
        self.prochain_titre = QLabel(self.cadre_prochain)
        self.prochain_titre.setObjectName(u"prochain_titre")
        self.prochain_titre.setFont(font3)
        self.prochain_titre.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.prochain_titre.setWordWrap(True)

        self.ligne_prochain_titre.addWidget(self.prochain_titre)

        self.ouvrir_sonore_prochain = QToolButton(self.cadre_prochain)
        self.ouvrir_sonore_prochain.setObjectName(u"ouvrir_sonore_prochain")
        self.ouvrir_sonore_prochain.setEnabled(False)

        self.ligne_prochain_titre.addWidget(self.ouvrir_sonore_prochain)

        self.ligne_prochain_titre.setStretch(0, 1)

        self.disposition_prochain.addLayout(self.ligne_prochain_titre)

        self.formulaire_prochain = QFormLayout()
        self.formulaire_prochain.setObjectName(u"formulaire_prochain")
        self.intitule_prochain_evenement = QLabel(self.cadre_prochain)
        self.intitule_prochain_evenement.setObjectName(u"intitule_prochain_evenement")

        self.formulaire_prochain.setWidget(0, QFormLayout.ItemRole.LabelRole, self.intitule_prochain_evenement)

        self.ligne_prochain_evenement = QHBoxLayout()
        self.ligne_prochain_evenement.setObjectName(u"ligne_prochain_evenement")
        self.prochain_evenement = QLabel(self.cadre_prochain)
        self.prochain_evenement.setObjectName(u"prochain_evenement")
        self.prochain_evenement.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.prochain_evenement.setWordWrap(True)

        self.ligne_prochain_evenement.addWidget(self.prochain_evenement)

        self.ouvrir_evenement_prochain = QToolButton(self.cadre_prochain)
        self.ouvrir_evenement_prochain.setObjectName(u"ouvrir_evenement_prochain")
        self.ouvrir_evenement_prochain.setEnabled(False)

        self.ligne_prochain_evenement.addWidget(self.ouvrir_evenement_prochain)

        self.ligne_prochain_evenement.setStretch(0, 1)

        self.formulaire_prochain.setLayout(0, QFormLayout.ItemRole.FieldRole, self.ligne_prochain_evenement)

        self.intitule_prochain_sequence = QLabel(self.cadre_prochain)
        self.intitule_prochain_sequence.setObjectName(u"intitule_prochain_sequence")

        self.formulaire_prochain.setWidget(1, QFormLayout.ItemRole.LabelRole, self.intitule_prochain_sequence)

        self.ligne_prochain_sequence = QHBoxLayout()
        self.ligne_prochain_sequence.setObjectName(u"ligne_prochain_sequence")
        self.prochain_sequence = QLabel(self.cadre_prochain)
        self.prochain_sequence.setObjectName(u"prochain_sequence")
        self.prochain_sequence.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.prochain_sequence.setWordWrap(True)

        self.ligne_prochain_sequence.addWidget(self.prochain_sequence)

        self.ouvrir_sequence_prochain = QToolButton(self.cadre_prochain)
        self.ouvrir_sequence_prochain.setObjectName(u"ouvrir_sequence_prochain")
        self.ouvrir_sequence_prochain.setEnabled(False)

        self.ligne_prochain_sequence.addWidget(self.ouvrir_sequence_prochain)

        self.ligne_prochain_sequence.setStretch(0, 1)

        self.formulaire_prochain.setLayout(1, QFormLayout.ItemRole.FieldRole, self.ligne_prochain_sequence)

        self.intitule_prochain_banque = QLabel(self.cadre_prochain)
        self.intitule_prochain_banque.setObjectName(u"intitule_prochain_banque")

        self.formulaire_prochain.setWidget(2, QFormLayout.ItemRole.LabelRole, self.intitule_prochain_banque)

        self.ligne_prochain_banque = QHBoxLayout()
        self.ligne_prochain_banque.setObjectName(u"ligne_prochain_banque")
        self.prochain_banque = QLabel(self.cadre_prochain)
        self.prochain_banque.setObjectName(u"prochain_banque")
        self.prochain_banque.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.prochain_banque.setWordWrap(True)

        self.ligne_prochain_banque.addWidget(self.prochain_banque)

        self.ouvrir_banque_prochain = QToolButton(self.cadre_prochain)
        self.ouvrir_banque_prochain.setObjectName(u"ouvrir_banque_prochain")
        self.ouvrir_banque_prochain.setEnabled(False)

        self.ligne_prochain_banque.addWidget(self.ouvrir_banque_prochain)

        self.ligne_prochain_banque.setStretch(0, 1)

        self.formulaire_prochain.setLayout(2, QFormLayout.ItemRole.FieldRole, self.ligne_prochain_banque)

        self.intitule_prochain_horaire = QLabel(self.cadre_prochain)
        self.intitule_prochain_horaire.setObjectName(u"intitule_prochain_horaire")

        self.formulaire_prochain.setWidget(3, QFormLayout.ItemRole.LabelRole, self.intitule_prochain_horaire)

        self.prochain_horaire = QLabel(self.cadre_prochain)
        self.prochain_horaire.setObjectName(u"prochain_horaire")
        self.prochain_horaire.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.prochain_horaire.setWordWrap(True)

        self.formulaire_prochain.setWidget(3, QFormLayout.ItemRole.FieldRole, self.prochain_horaire)

        self.intitule_prochain_emplacement = QLabel(self.cadre_prochain)
        self.intitule_prochain_emplacement.setObjectName(u"intitule_prochain_emplacement")

        self.formulaire_prochain.setWidget(4, QFormLayout.ItemRole.LabelRole, self.intitule_prochain_emplacement)

        self.prochain_emplacement = QLineEdit(self.cadre_prochain)
        self.prochain_emplacement.setObjectName(u"prochain_emplacement")
        self.prochain_emplacement.setFrame(False)
        self.prochain_emplacement.setReadOnly(True)

        self.formulaire_prochain.setWidget(4, QFormLayout.ItemRole.FieldRole, self.prochain_emplacement)

        self.intitule_prochain_sain = QLabel(self.cadre_prochain)
        self.intitule_prochain_sain.setObjectName(u"intitule_prochain_sain")

        self.formulaire_prochain.setWidget(5, QFormLayout.ItemRole.LabelRole, self.intitule_prochain_sain)

        self.prochain_sain = QLabel(self.cadre_prochain)
        self.prochain_sain.setObjectName(u"prochain_sain")
        self.prochain_sain.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.formulaire_prochain.setWidget(5, QFormLayout.ItemRole.FieldRole, self.prochain_sain)


        self.disposition_prochain.addLayout(self.formulaire_prochain)


        self.sonores.addWidget(self.cadre_prochain)

        self.sonores.setStretch(0, 1)
        self.sonores.setStretch(2, 1)

        self.disposition.addLayout(self.sonores)

        self.cadre_airplay = QGroupBox(EcranParDefaut)
        self.cadre_airplay.setObjectName(u"cadre_airplay")
        self.disposition_airplay = QVBoxLayout(self.cadre_airplay)
        self.disposition_airplay.setObjectName(u"disposition_airplay")
        self.table_airplay = QTableView(self.cadre_airplay)
        self.table_airplay.setObjectName(u"table_airplay")
        self.table_airplay.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_airplay.setAlternatingRowColors(True)
        self.table_airplay.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_airplay.horizontalHeader().setStretchLastSection(True)
        self.table_airplay.verticalHeader().setVisible(False)

        self.disposition_airplay.addWidget(self.table_airplay)


        self.disposition.addWidget(self.cadre_airplay)


        self.retranslateUi(EcranParDefaut)

        QMetaObject.connectSlotsByName(EcranParDefaut)
    # setupUi

    def retranslateUi(self, EcranParDefaut):
        EcranParDefaut.setWindowTitle(QCoreApplication.translate("EcranParDefaut", u"MachinCast", None))
        self.heure.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
#if QT_CONFIG(tooltip)
        self.texte_public.setToolTip(QCoreApplication.translate("EcranParDefaut", u"Ce que les sorties publiques affichent du sonore en cours", None))
#endif // QT_CONFIG(tooltip)
        self.texte_public.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
#if QT_CONFIG(tooltip)
        self.etat_lecture.setToolTip(QCoreApplication.translate("EcranParDefaut", u"\u00c9tat de Machin lecture", None))
#endif // QT_CONFIG(tooltip)
        self.etat_lecture.setText(QCoreApplication.translate("EcranParDefaut", u"\u00c0 l'arr\u00eat", None))
#if QT_CONFIG(tooltip)
        self.evenement_antenne.setToolTip(QCoreApplication.translate("EcranParDefaut", u"\u00c9v\u00e9nement \u00e0 l'antenne", None))
#endif // QT_CONFIG(tooltip)
        self.evenement_antenne.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.cadre_en_cours.setTitle(QCoreApplication.translate("EcranParDefaut", u"Sonore en cours", None))
        self.en_cours_titre.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
#if QT_CONFIG(tooltip)
        self.ouvrir_sonore_en_cours.setToolTip(QCoreApplication.translate("EcranParDefaut", u"Ouvrir la fiche du sonore", None))
#endif // QT_CONFIG(tooltip)
        self.ouvrir_sonore_en_cours.setText(QCoreApplication.translate("EcranParDefaut", u"Fiche\u2026", None))
        self.intitule_en_cours_evenement.setText(QCoreApplication.translate("EcranParDefaut", u"\u00c9v\u00e9nement", None))
        self.en_cours_evenement.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
#if QT_CONFIG(tooltip)
        self.ouvrir_evenement_en_cours.setToolTip(QCoreApplication.translate("EcranParDefaut", u"Ouvrir la fiche de l'\u00e9v\u00e9nement", None))
#endif // QT_CONFIG(tooltip)
        self.ouvrir_evenement_en_cours.setText(QCoreApplication.translate("EcranParDefaut", u"Fiche\u2026", None))
        self.intitule_en_cours_sequence.setText(QCoreApplication.translate("EcranParDefaut", u"S\u00e9quence", None))
        self.en_cours_sequence.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
#if QT_CONFIG(tooltip)
        self.ouvrir_sequence_en_cours.setToolTip(QCoreApplication.translate("EcranParDefaut", u"Ouvrir la fiche de la s\u00e9quence", None))
#endif // QT_CONFIG(tooltip)
        self.ouvrir_sequence_en_cours.setText(QCoreApplication.translate("EcranParDefaut", u"Fiche\u2026", None))
        self.intitule_en_cours_banque.setText(QCoreApplication.translate("EcranParDefaut", u"Banque", None))
        self.en_cours_banque.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
#if QT_CONFIG(tooltip)
        self.ouvrir_banque_en_cours.setToolTip(QCoreApplication.translate("EcranParDefaut", u"Ouvrir la fiche de la banque", None))
#endif // QT_CONFIG(tooltip)
        self.ouvrir_banque_en_cours.setText(QCoreApplication.translate("EcranParDefaut", u"Fiche\u2026", None))
        self.intitule_en_cours_horaire.setText(QCoreApplication.translate("EcranParDefaut", u"Horaire", None))
        self.en_cours_horaire.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.intitule_en_cours_emplacement.setText(QCoreApplication.translate("EcranParDefaut", u"Emplacement", None))
        self.en_cours_emplacement.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.en_cours_progression.setFormat(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.colonne_antenne.setTitle(QCoreApplication.translate("EcranParDefaut", u"Antenne", None))
#if QT_CONFIG(tooltip)
        self.voyant_saturation.setToolTip(QCoreApplication.translate("EcranParDefaut", u"Une cr\u00eate \u00e0 -1 dBFS ou plus, dans les 3 derni\u00e8res secondes", None))
#endif // QT_CONFIG(tooltip)
        self.voyant_saturation.setText(QCoreApplication.translate("EcranParDefaut", u"Saturation", None))
#if QT_CONFIG(tooltip)
        self.voyant_silence.setToolTip(QCoreApplication.translate("EcranParDefaut", u"Plus de 5 secondes sous -50 dBFS", None))
#endif // QT_CONFIG(tooltip)
        self.voyant_silence.setText(QCoreApplication.translate("EcranParDefaut", u"Silence", None))
        self.etat_moniteur.setText("")
        self.cadre_prochain.setTitle(QCoreApplication.translate("EcranParDefaut", u"Prochain sonore", None))
        self.prochain_titre.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
#if QT_CONFIG(tooltip)
        self.ouvrir_sonore_prochain.setToolTip(QCoreApplication.translate("EcranParDefaut", u"Ouvrir la fiche du sonore", None))
#endif // QT_CONFIG(tooltip)
        self.ouvrir_sonore_prochain.setText(QCoreApplication.translate("EcranParDefaut", u"Fiche\u2026", None))
        self.intitule_prochain_evenement.setText(QCoreApplication.translate("EcranParDefaut", u"\u00c9v\u00e9nement", None))
        self.prochain_evenement.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
#if QT_CONFIG(tooltip)
        self.ouvrir_evenement_prochain.setToolTip(QCoreApplication.translate("EcranParDefaut", u"Ouvrir la fiche de l'\u00e9v\u00e9nement", None))
#endif // QT_CONFIG(tooltip)
        self.ouvrir_evenement_prochain.setText(QCoreApplication.translate("EcranParDefaut", u"Fiche\u2026", None))
        self.intitule_prochain_sequence.setText(QCoreApplication.translate("EcranParDefaut", u"S\u00e9quence", None))
        self.prochain_sequence.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
#if QT_CONFIG(tooltip)
        self.ouvrir_sequence_prochain.setToolTip(QCoreApplication.translate("EcranParDefaut", u"Ouvrir la fiche de la s\u00e9quence", None))
#endif // QT_CONFIG(tooltip)
        self.ouvrir_sequence_prochain.setText(QCoreApplication.translate("EcranParDefaut", u"Fiche\u2026", None))
        self.intitule_prochain_banque.setText(QCoreApplication.translate("EcranParDefaut", u"Banque", None))
        self.prochain_banque.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
#if QT_CONFIG(tooltip)
        self.ouvrir_banque_prochain.setToolTip(QCoreApplication.translate("EcranParDefaut", u"Ouvrir la fiche de la banque", None))
#endif // QT_CONFIG(tooltip)
        self.ouvrir_banque_prochain.setText(QCoreApplication.translate("EcranParDefaut", u"Fiche\u2026", None))
        self.intitule_prochain_horaire.setText(QCoreApplication.translate("EcranParDefaut", u"Horaire estim\u00e9", None))
        self.prochain_horaire.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.intitule_prochain_emplacement.setText(QCoreApplication.translate("EcranParDefaut", u"Emplacement", None))
        self.prochain_emplacement.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.intitule_prochain_sain.setText(QCoreApplication.translate("EcranParDefaut", u"Sain", None))
        self.prochain_sain.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.cadre_airplay.setTitle(QCoreApplication.translate("EcranParDefaut", u"Airplay des 12 derni\u00e8res heures", None))
#if QT_CONFIG(tooltip)
        self.table_airplay.setToolTip(QCoreApplication.translate("EcranParDefaut", u"Double-clic sur un sonore, un \u00e9v\u00e9nement, une s\u00e9quence ou une banque : ouvrir sa fiche", None))
#endif // QT_CONFIG(tooltip)
    # retranslateUi

