# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'fiche_banque.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QFormLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QSpacerItem, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget)

class Ui_FicheBanque(object):
    def setupUi(self, FicheBanque):
        if not FicheBanque.objectName():
            FicheBanque.setObjectName(u"FicheBanque")
        FicheBanque.resize(1100, 700)
        self.disposition = QVBoxLayout(FicheBanque)
        self.disposition.setObjectName(u"disposition")
        self.formulaire = QFormLayout()
        self.formulaire.setObjectName(u"formulaire")
        self.etiquette_nom_interne = QLabel(FicheBanque)
        self.etiquette_nom_interne.setObjectName(u"etiquette_nom_interne")

        self.formulaire.setWidget(0, QFormLayout.ItemRole.LabelRole, self.etiquette_nom_interne)

        self.nom_interne = QLineEdit(FicheBanque)
        self.nom_interne.setObjectName(u"nom_interne")
        self.nom_interne.setMaxLength(255)

        self.formulaire.setWidget(0, QFormLayout.ItemRole.FieldRole, self.nom_interne)

        self.etiquette_nom_public = QLabel(FicheBanque)
        self.etiquette_nom_public.setObjectName(u"etiquette_nom_public")

        self.formulaire.setWidget(1, QFormLayout.ItemRole.LabelRole, self.etiquette_nom_public)

        self.nom_public = QLineEdit(FicheBanque)
        self.nom_public.setObjectName(u"nom_public")
        self.nom_public.setMaxLength(255)

        self.formulaire.setWidget(1, QFormLayout.ItemRole.FieldRole, self.nom_public)

        self.etiquette_mode = QLabel(FicheBanque)
        self.etiquette_mode.setObjectName(u"etiquette_mode")

        self.formulaire.setWidget(2, QFormLayout.ItemRole.LabelRole, self.etiquette_mode)

        self.mode = QComboBox(FicheBanque)
        self.mode.setObjectName(u"mode")

        self.formulaire.setWidget(2, QFormLayout.ItemRole.FieldRole, self.mode)

        self.etiquette_masquage = QLabel(FicheBanque)
        self.etiquette_masquage.setObjectName(u"etiquette_masquage")

        self.formulaire.setWidget(3, QFormLayout.ItemRole.LabelRole, self.etiquette_masquage)

        self.masquage = QComboBox(FicheBanque)
        self.masquage.setObjectName(u"masquage")

        self.formulaire.setWidget(3, QFormLayout.ItemRole.FieldRole, self.masquage)

        self.ne_pas_repeter = QCheckBox(FicheBanque)
        self.ne_pas_repeter.setObjectName(u"ne_pas_repeter")

        self.formulaire.setWidget(4, QFormLayout.ItemRole.FieldRole, self.ne_pas_repeter)


        self.disposition.addLayout(self.formulaire)

        self.listes = QHBoxLayout()
        self.listes.setObjectName(u"listes")
        self.groupe_repertoires = QGroupBox(FicheBanque)
        self.groupe_repertoires.setObjectName(u"groupe_repertoires")
        self.disposition_repertoires = QVBoxLayout(self.groupe_repertoires)
        self.disposition_repertoires.setObjectName(u"disposition_repertoires")
        self.explication_repertoires = QLabel(self.groupe_repertoires)
        self.explication_repertoires.setObjectName(u"explication_repertoires")
        self.explication_repertoires.setWordWrap(True)

        self.disposition_repertoires.addWidget(self.explication_repertoires)

        self.repertoires = QListWidget(self.groupe_repertoires)
        self.repertoires.setObjectName(u"repertoires")
        self.repertoires.setAlternatingRowColors(True)

        self.disposition_repertoires.addWidget(self.repertoires)

        self.boutons_repertoires = QHBoxLayout()
        self.boutons_repertoires.setObjectName(u"boutons_repertoires")
        self.ajouter_repertoire = QPushButton(self.groupe_repertoires)
        self.ajouter_repertoire.setObjectName(u"ajouter_repertoire")

        self.boutons_repertoires.addWidget(self.ajouter_repertoire)

        self.retirer_repertoire = QPushButton(self.groupe_repertoires)
        self.retirer_repertoire.setObjectName(u"retirer_repertoire")

        self.boutons_repertoires.addWidget(self.retirer_repertoire)


        self.disposition_repertoires.addLayout(self.boutons_repertoires)


        self.listes.addWidget(self.groupe_repertoires)

        self.groupe_sonores = QGroupBox(FicheBanque)
        self.groupe_sonores.setObjectName(u"groupe_sonores")
        self.disposition_sonores = QVBoxLayout(self.groupe_sonores)
        self.disposition_sonores.setObjectName(u"disposition_sonores")
        self.sonores = QTreeWidget(self.groupe_sonores)
        self.sonores.setObjectName(u"sonores")
        self.sonores.setAlternatingRowColors(True)
        self.sonores.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.sonores.setRootIsDecorated(False)
        self.sonores.setUniformRowHeights(True)

        self.disposition_sonores.addWidget(self.sonores)

        self.boutons_sonores = QHBoxLayout()
        self.boutons_sonores.setObjectName(u"boutons_sonores")
        self.ajouter_sonores = QPushButton(self.groupe_sonores)
        self.ajouter_sonores.setObjectName(u"ajouter_sonores")

        self.boutons_sonores.addWidget(self.ajouter_sonores)

        self.retirer_sonore = QPushButton(self.groupe_sonores)
        self.retirer_sonore.setObjectName(u"retirer_sonore")

        self.boutons_sonores.addWidget(self.retirer_sonore)

        self.espace_sonores = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.boutons_sonores.addItem(self.espace_sonores)

        self.monter = QPushButton(self.groupe_sonores)
        self.monter.setObjectName(u"monter")

        self.boutons_sonores.addWidget(self.monter)

        self.descendre = QPushButton(self.groupe_sonores)
        self.descendre.setObjectName(u"descendre")

        self.boutons_sonores.addWidget(self.descendre)


        self.disposition_sonores.addLayout(self.boutons_sonores)


        self.listes.addWidget(self.groupe_sonores)

        self.listes.setStretch(0, 1)
        self.listes.setStretch(1, 2)

        self.disposition.addLayout(self.listes)

        self.pied = QHBoxLayout()
        self.pied.setObjectName(u"pied")
        self.message = QLabel(FicheBanque)
        self.message.setObjectName(u"message")
        self.message.setWordWrap(True)

        self.pied.addWidget(self.message)

        self.annuler = QPushButton(FicheBanque)
        self.annuler.setObjectName(u"annuler")

        self.pied.addWidget(self.annuler)

        self.enregistrer = QPushButton(FicheBanque)
        self.enregistrer.setObjectName(u"enregistrer")

        self.pied.addWidget(self.enregistrer)

        self.pied.setStretch(0, 1)

        self.disposition.addLayout(self.pied)

        self.disposition.setStretch(1, 1)
#if QT_CONFIG(shortcut)
        self.etiquette_nom_interne.setBuddy(self.nom_interne)
        self.etiquette_nom_public.setBuddy(self.nom_public)
        self.etiquette_mode.setBuddy(self.mode)
        self.etiquette_masquage.setBuddy(self.masquage)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(FicheBanque)

        self.enregistrer.setDefault(True)


        QMetaObject.connectSlotsByName(FicheBanque)
    # setupUi

    def retranslateUi(self, FicheBanque):
        self.etiquette_nom_interne.setText(QCoreApplication.translate("FicheBanque", u"&Nom interne", None))
        self.nom_interne.setPlaceholderText(QCoreApplication.translate("FicheBanque", u"Obligatoire, et propre \u00e0 cette banque", None))
        self.etiquette_nom_public.setText(QCoreApplication.translate("FicheBanque", u"Nom &public", None))
        self.nom_public.setPlaceholderText(QCoreApplication.translate("FicheBanque", u"Affich\u00e9 \u00e0 la place de l'artiste et du titre masqu\u00e9s ; facultatif", None))
        self.etiquette_mode.setText(QCoreApplication.translate("FicheBanque", u"&Mode", None))
        self.etiquette_masquage.setText(QCoreApplication.translate("FicheBanque", u"&Artiste et titre", None))
        self.ne_pas_repeter.setText(QCoreApplication.translate("FicheBanque", u"Ne pas &r\u00e9p\u00e9ter : la banque ne passe jamais deux fois de suite", None))
        self.groupe_repertoires.setTitle(QCoreApplication.translate("FicheBanque", u"R\u00e9pertoires index\u00e9s", None))
        self.explication_repertoires.setText(QCoreApplication.translate("FicheBanque", u"Machin indexation rattache \u00e0 la banque les fichiers sonores de ces r\u00e9pertoires et de leurs sous-r\u00e9pertoires.", None))
        self.ajouter_repertoire.setText(QCoreApplication.translate("FicheBanque", u"Ajouter un r\u00e9pertoire\u2026", None))
        self.retirer_repertoire.setText(QCoreApplication.translate("FicheBanque", u"Retirer le r\u00e9pertoire", None))
        self.groupe_sonores.setTitle(QCoreApplication.translate("FicheBanque", u"Sonores", None))
        ___qtreewidgetitem = self.sonores.headerItem()
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("FicheBanque", u"Emplacement", None))
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("FicheBanque", u"Dur\u00e9e", None))
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("FicheBanque", u"Sonore", None))
        self.ajouter_sonores.setText(QCoreApplication.translate("FicheBanque", u"Ajouter des sonores\u2026", None))
        self.retirer_sonore.setText(QCoreApplication.translate("FicheBanque", u"Retirer le sonore", None))
        self.monter.setText(QCoreApplication.translate("FicheBanque", u"Monter", None))
        self.descendre.setText(QCoreApplication.translate("FicheBanque", u"Descendre", None))
        self.annuler.setText(QCoreApplication.translate("FicheBanque", u"Annuler", None))
        self.enregistrer.setText(QCoreApplication.translate("FicheBanque", u"Enregistrer", None))
        pass
    # retranslateUi

