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
    QProgressBar, QSizePolicy, QSpacerItem, QTableView,
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

        self.espace_bandeau = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.bandeau.addItem(self.espace_bandeau)

        self.intitule_etat_lecture = QLabel(EcranParDefaut)
        self.intitule_etat_lecture.setObjectName(u"intitule_etat_lecture")

        self.bandeau.addWidget(self.intitule_etat_lecture)

        self.etat_lecture = QLabel(EcranParDefaut)
        self.etat_lecture.setObjectName(u"etat_lecture")
        font1 = QFont()
        font1.setPointSize(12)
        font1.setBold(True)
        self.etat_lecture.setFont(font1)
        self.etat_lecture.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.bandeau.addWidget(self.etat_lecture)


        self.disposition.addLayout(self.bandeau)

        self.sonores = QHBoxLayout()
        self.sonores.setObjectName(u"sonores")
        self.cadre_en_cours = QGroupBox(EcranParDefaut)
        self.cadre_en_cours.setObjectName(u"cadre_en_cours")
        self.disposition_en_cours = QVBoxLayout(self.cadre_en_cours)
        self.disposition_en_cours.setObjectName(u"disposition_en_cours")
        self.en_cours_titre = QLabel(self.cadre_en_cours)
        self.en_cours_titre.setObjectName(u"en_cours_titre")
        font2 = QFont()
        font2.setPointSize(14)
        font2.setBold(True)
        self.en_cours_titre.setFont(font2)
        self.en_cours_titre.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.en_cours_titre.setWordWrap(True)

        self.disposition_en_cours.addWidget(self.en_cours_titre)

        self.formulaire_en_cours = QFormLayout()
        self.formulaire_en_cours.setObjectName(u"formulaire_en_cours")
        self.intitule_en_cours_evenement = QLabel(self.cadre_en_cours)
        self.intitule_en_cours_evenement.setObjectName(u"intitule_en_cours_evenement")

        self.formulaire_en_cours.setWidget(0, QFormLayout.ItemRole.LabelRole, self.intitule_en_cours_evenement)

        self.en_cours_evenement = QLabel(self.cadre_en_cours)
        self.en_cours_evenement.setObjectName(u"en_cours_evenement")
        self.en_cours_evenement.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.en_cours_evenement.setWordWrap(True)

        self.formulaire_en_cours.setWidget(0, QFormLayout.ItemRole.FieldRole, self.en_cours_evenement)

        self.intitule_en_cours_emplacement = QLabel(self.cadre_en_cours)
        self.intitule_en_cours_emplacement.setObjectName(u"intitule_en_cours_emplacement")

        self.formulaire_en_cours.setWidget(1, QFormLayout.ItemRole.LabelRole, self.intitule_en_cours_emplacement)

        self.en_cours_emplacement = QLineEdit(self.cadre_en_cours)
        self.en_cours_emplacement.setObjectName(u"en_cours_emplacement")
        self.en_cours_emplacement.setFrame(False)
        self.en_cours_emplacement.setReadOnly(True)

        self.formulaire_en_cours.setWidget(1, QFormLayout.ItemRole.FieldRole, self.en_cours_emplacement)

        self.intitule_en_cours_debut = QLabel(self.cadre_en_cours)
        self.intitule_en_cours_debut.setObjectName(u"intitule_en_cours_debut")

        self.formulaire_en_cours.setWidget(2, QFormLayout.ItemRole.LabelRole, self.intitule_en_cours_debut)

        self.en_cours_debut = QLabel(self.cadre_en_cours)
        self.en_cours_debut.setObjectName(u"en_cours_debut")
        self.en_cours_debut.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.formulaire_en_cours.setWidget(2, QFormLayout.ItemRole.FieldRole, self.en_cours_debut)

        self.intitule_en_cours_duree = QLabel(self.cadre_en_cours)
        self.intitule_en_cours_duree.setObjectName(u"intitule_en_cours_duree")

        self.formulaire_en_cours.setWidget(3, QFormLayout.ItemRole.LabelRole, self.intitule_en_cours_duree)

        self.en_cours_duree = QLabel(self.cadre_en_cours)
        self.en_cours_duree.setObjectName(u"en_cours_duree")
        self.en_cours_duree.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.formulaire_en_cours.setWidget(3, QFormLayout.ItemRole.FieldRole, self.en_cours_duree)

        self.intitule_en_cours_fin = QLabel(self.cadre_en_cours)
        self.intitule_en_cours_fin.setObjectName(u"intitule_en_cours_fin")

        self.formulaire_en_cours.setWidget(4, QFormLayout.ItemRole.LabelRole, self.intitule_en_cours_fin)

        self.en_cours_fin = QLabel(self.cadre_en_cours)
        self.en_cours_fin.setObjectName(u"en_cours_fin")
        self.en_cours_fin.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.formulaire_en_cours.setWidget(4, QFormLayout.ItemRole.FieldRole, self.en_cours_fin)

        self.intitule_en_cours_progression = QLabel(self.cadre_en_cours)
        self.intitule_en_cours_progression.setObjectName(u"intitule_en_cours_progression")

        self.formulaire_en_cours.setWidget(5, QFormLayout.ItemRole.LabelRole, self.intitule_en_cours_progression)

        self.en_cours_progression = QProgressBar(self.cadre_en_cours)
        self.en_cours_progression.setObjectName(u"en_cours_progression")
        self.en_cours_progression.setMaximum(100)
        self.en_cours_progression.setValue(0)

        self.formulaire_en_cours.setWidget(5, QFormLayout.ItemRole.FieldRole, self.en_cours_progression)


        self.disposition_en_cours.addLayout(self.formulaire_en_cours)


        self.sonores.addWidget(self.cadre_en_cours)

        self.cadre_prochain = QGroupBox(EcranParDefaut)
        self.cadre_prochain.setObjectName(u"cadre_prochain")
        self.disposition_prochain = QVBoxLayout(self.cadre_prochain)
        self.disposition_prochain.setObjectName(u"disposition_prochain")
        self.prochain_titre = QLabel(self.cadre_prochain)
        self.prochain_titre.setObjectName(u"prochain_titre")
        font3 = QFont()
        font3.setBold(True)
        self.prochain_titre.setFont(font3)
        self.prochain_titre.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.prochain_titre.setWordWrap(True)

        self.disposition_prochain.addWidget(self.prochain_titre)

        self.formulaire_prochain = QFormLayout()
        self.formulaire_prochain.setObjectName(u"formulaire_prochain")
        self.intitule_prochain_evenement = QLabel(self.cadre_prochain)
        self.intitule_prochain_evenement.setObjectName(u"intitule_prochain_evenement")

        self.formulaire_prochain.setWidget(0, QFormLayout.ItemRole.LabelRole, self.intitule_prochain_evenement)

        self.prochain_evenement = QLabel(self.cadre_prochain)
        self.prochain_evenement.setObjectName(u"prochain_evenement")
        self.prochain_evenement.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.prochain_evenement.setWordWrap(True)

        self.formulaire_prochain.setWidget(0, QFormLayout.ItemRole.FieldRole, self.prochain_evenement)

        self.intitule_prochain_emplacement = QLabel(self.cadre_prochain)
        self.intitule_prochain_emplacement.setObjectName(u"intitule_prochain_emplacement")

        self.formulaire_prochain.setWidget(1, QFormLayout.ItemRole.LabelRole, self.intitule_prochain_emplacement)

        self.prochain_emplacement = QLineEdit(self.cadre_prochain)
        self.prochain_emplacement.setObjectName(u"prochain_emplacement")
        self.prochain_emplacement.setFrame(False)
        self.prochain_emplacement.setReadOnly(True)

        self.formulaire_prochain.setWidget(1, QFormLayout.ItemRole.FieldRole, self.prochain_emplacement)

        self.intitule_prochain_debut = QLabel(self.cadre_prochain)
        self.intitule_prochain_debut.setObjectName(u"intitule_prochain_debut")

        self.formulaire_prochain.setWidget(2, QFormLayout.ItemRole.LabelRole, self.intitule_prochain_debut)

        self.prochain_debut = QLabel(self.cadre_prochain)
        self.prochain_debut.setObjectName(u"prochain_debut")
        self.prochain_debut.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.formulaire_prochain.setWidget(2, QFormLayout.ItemRole.FieldRole, self.prochain_debut)

        self.intitule_prochain_fin = QLabel(self.cadre_prochain)
        self.intitule_prochain_fin.setObjectName(u"intitule_prochain_fin")

        self.formulaire_prochain.setWidget(3, QFormLayout.ItemRole.LabelRole, self.intitule_prochain_fin)

        self.prochain_fin = QLabel(self.cadre_prochain)
        self.prochain_fin.setObjectName(u"prochain_fin")
        self.prochain_fin.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.formulaire_prochain.setWidget(3, QFormLayout.ItemRole.FieldRole, self.prochain_fin)

        self.intitule_prochain_duree = QLabel(self.cadre_prochain)
        self.intitule_prochain_duree.setObjectName(u"intitule_prochain_duree")

        self.formulaire_prochain.setWidget(4, QFormLayout.ItemRole.LabelRole, self.intitule_prochain_duree)

        self.prochain_duree = QLabel(self.cadre_prochain)
        self.prochain_duree.setObjectName(u"prochain_duree")
        self.prochain_duree.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.formulaire_prochain.setWidget(4, QFormLayout.ItemRole.FieldRole, self.prochain_duree)

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
        self.sonores.setStretch(1, 1)

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
        self.intitule_etat_lecture.setText(QCoreApplication.translate("EcranParDefaut", u"Binaire lecture :", None))
        self.etat_lecture.setText(QCoreApplication.translate("EcranParDefaut", u"\u00c0 l'arr\u00eat", None))
        self.cadre_en_cours.setTitle(QCoreApplication.translate("EcranParDefaut", u"Sonore en cours", None))
        self.en_cours_titre.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.intitule_en_cours_evenement.setText(QCoreApplication.translate("EcranParDefaut", u"\u00c9v\u00e9nement", None))
        self.en_cours_evenement.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.intitule_en_cours_emplacement.setText(QCoreApplication.translate("EcranParDefaut", u"Emplacement", None))
        self.en_cours_emplacement.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.intitule_en_cours_debut.setText(QCoreApplication.translate("EcranParDefaut", u"D\u00e9but", None))
        self.en_cours_debut.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.intitule_en_cours_duree.setText(QCoreApplication.translate("EcranParDefaut", u"Dur\u00e9e", None))
        self.en_cours_duree.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.intitule_en_cours_fin.setText(QCoreApplication.translate("EcranParDefaut", u"Fin estim\u00e9e", None))
        self.en_cours_fin.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.intitule_en_cours_progression.setText(QCoreApplication.translate("EcranParDefaut", u"Progression", None))
        self.en_cours_progression.setFormat(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.cadre_prochain.setTitle(QCoreApplication.translate("EcranParDefaut", u"Prochain sonore", None))
        self.prochain_titre.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.intitule_prochain_evenement.setText(QCoreApplication.translate("EcranParDefaut", u"\u00c9v\u00e9nement", None))
        self.prochain_evenement.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.intitule_prochain_emplacement.setText(QCoreApplication.translate("EcranParDefaut", u"Emplacement", None))
        self.prochain_emplacement.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.intitule_prochain_debut.setText(QCoreApplication.translate("EcranParDefaut", u"D\u00e9but estim\u00e9", None))
        self.prochain_debut.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.intitule_prochain_fin.setText(QCoreApplication.translate("EcranParDefaut", u"Fin estim\u00e9e", None))
        self.prochain_fin.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.intitule_prochain_duree.setText(QCoreApplication.translate("EcranParDefaut", u"Dur\u00e9e", None))
        self.prochain_duree.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.intitule_prochain_sain.setText(QCoreApplication.translate("EcranParDefaut", u"Sain", None))
        self.prochain_sain.setText(QCoreApplication.translate("EcranParDefaut", u"\u2014", None))
        self.cadre_airplay.setTitle(QCoreApplication.translate("EcranParDefaut", u"Airplay des 12 derni\u00e8res heures", None))
    # retranslateUi

