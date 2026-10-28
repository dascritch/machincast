# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'fiche_sequence.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QFormLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPushButton,
    QSizePolicy, QSpacerItem, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget)

class Ui_FicheSequence(object):
    def setupUi(self, FicheSequence):
        if not FicheSequence.objectName():
            FicheSequence.setObjectName(u"FicheSequence")
        FicheSequence.resize(1100, 700)
        self.disposition = QVBoxLayout(FicheSequence)
        self.disposition.setObjectName(u"disposition")
        self.formulaire = QFormLayout()
        self.formulaire.setObjectName(u"formulaire")
        self.etiquette_nom_interne = QLabel(FicheSequence)
        self.etiquette_nom_interne.setObjectName(u"etiquette_nom_interne")

        self.formulaire.setWidget(0, QFormLayout.ItemRole.LabelRole, self.etiquette_nom_interne)

        self.nom_interne = QLineEdit(FicheSequence)
        self.nom_interne.setObjectName(u"nom_interne")
        self.nom_interne.setMaxLength(255)

        self.formulaire.setWidget(0, QFormLayout.ItemRole.FieldRole, self.nom_interne)

        self.etiquette_nom_public = QLabel(FicheSequence)
        self.etiquette_nom_public.setObjectName(u"etiquette_nom_public")

        self.formulaire.setWidget(1, QFormLayout.ItemRole.LabelRole, self.etiquette_nom_public)

        self.nom_public = QLineEdit(FicheSequence)
        self.nom_public.setObjectName(u"nom_public")
        self.nom_public.setMaxLength(255)

        self.formulaire.setWidget(1, QFormLayout.ItemRole.FieldRole, self.nom_public)

        self.etiquette_masquage = QLabel(FicheSequence)
        self.etiquette_masquage.setObjectName(u"etiquette_masquage")

        self.formulaire.setWidget(2, QFormLayout.ItemRole.LabelRole, self.etiquette_masquage)

        self.masquage = QComboBox(FicheSequence)
        self.masquage.setObjectName(u"masquage")

        self.formulaire.setWidget(2, QFormLayout.ItemRole.FieldRole, self.masquage)


        self.disposition.addLayout(self.formulaire)

        self.listes = QHBoxLayout()
        self.listes.setObjectName(u"listes")
        self.groupe_elements = QGroupBox(FicheSequence)
        self.groupe_elements.setObjectName(u"groupe_elements")
        self.disposition_elements = QVBoxLayout(self.groupe_elements)
        self.disposition_elements.setObjectName(u"disposition_elements")
        self.elements = QTreeWidget(self.groupe_elements)
        self.elements.setObjectName(u"elements")
        self.elements.setAlternatingRowColors(True)
        self.elements.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.elements.setRootIsDecorated(False)
        self.elements.setUniformRowHeights(True)

        self.disposition_elements.addWidget(self.elements)

        self.avertissement = QLabel(self.groupe_elements)
        self.avertissement.setObjectName(u"avertissement")
        self.avertissement.setWordWrap(True)

        self.disposition_elements.addWidget(self.avertissement)

        self.boutons_elements = QHBoxLayout()
        self.boutons_elements.setObjectName(u"boutons_elements")
        self.ajouter_sonores = QPushButton(self.groupe_elements)
        self.ajouter_sonores.setObjectName(u"ajouter_sonores")

        self.boutons_elements.addWidget(self.ajouter_sonores)

        self.ajouter_banques = QPushButton(self.groupe_elements)
        self.ajouter_banques.setObjectName(u"ajouter_banques")

        self.boutons_elements.addWidget(self.ajouter_banques)

        self.retirer_element = QPushButton(self.groupe_elements)
        self.retirer_element.setObjectName(u"retirer_element")

        self.boutons_elements.addWidget(self.retirer_element)

        self.espace_elements = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.boutons_elements.addItem(self.espace_elements)

        self.monter = QPushButton(self.groupe_elements)
        self.monter.setObjectName(u"monter")

        self.boutons_elements.addWidget(self.monter)

        self.descendre = QPushButton(self.groupe_elements)
        self.descendre.setObjectName(u"descendre")

        self.boutons_elements.addWidget(self.descendre)


        self.disposition_elements.addLayout(self.boutons_elements)


        self.listes.addWidget(self.groupe_elements)

        self.groupe_evenements = QGroupBox(FicheSequence)
        self.groupe_evenements.setObjectName(u"groupe_evenements")
        self.disposition_evenements = QVBoxLayout(self.groupe_evenements)
        self.disposition_evenements.setObjectName(u"disposition_evenements")
        self.evenements = QListWidget(self.groupe_evenements)
        self.evenements.setObjectName(u"evenements")
        self.evenements.setAlternatingRowColors(True)

        self.disposition_evenements.addWidget(self.evenements)

        self.explication_evenements = QLabel(self.groupe_evenements)
        self.explication_evenements.setObjectName(u"explication_evenements")
        self.explication_evenements.setWordWrap(True)

        self.disposition_evenements.addWidget(self.explication_evenements)


        self.listes.addWidget(self.groupe_evenements)

        self.listes.setStretch(0, 2)
        self.listes.setStretch(1, 1)

        self.disposition.addLayout(self.listes)

        self.pied = QHBoxLayout()
        self.pied.setObjectName(u"pied")
        self.supprimer = QPushButton(FicheSequence)
        self.supprimer.setObjectName(u"supprimer")

        self.pied.addWidget(self.supprimer)

        self.dupliquer = QPushButton(FicheSequence)
        self.dupliquer.setObjectName(u"dupliquer")

        self.pied.addWidget(self.dupliquer)

        self.message = QLabel(FicheSequence)
        self.message.setObjectName(u"message")
        self.message.setWordWrap(True)

        self.pied.addWidget(self.message)

        self.annuler = QPushButton(FicheSequence)
        self.annuler.setObjectName(u"annuler")

        self.pied.addWidget(self.annuler)

        self.enregistrer = QPushButton(FicheSequence)
        self.enregistrer.setObjectName(u"enregistrer")

        self.pied.addWidget(self.enregistrer)

        self.pied.setStretch(2, 1)

        self.disposition.addLayout(self.pied)

        self.disposition.setStretch(1, 1)
#if QT_CONFIG(shortcut)
        self.etiquette_nom_interne.setBuddy(self.nom_interne)
        self.etiquette_nom_public.setBuddy(self.nom_public)
        self.etiquette_masquage.setBuddy(self.masquage)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(FicheSequence)

        self.enregistrer.setDefault(True)


        QMetaObject.connectSlotsByName(FicheSequence)
    # setupUi

    def retranslateUi(self, FicheSequence):
        self.etiquette_nom_interne.setText(QCoreApplication.translate("FicheSequence", u"&Nom interne", None))
        self.nom_interne.setPlaceholderText(QCoreApplication.translate("FicheSequence", u"Obligatoire, et propre \u00e0 cette s\u00e9quence", None))
        self.etiquette_nom_public.setText(QCoreApplication.translate("FicheSequence", u"Nom p&ublic", None))
        self.nom_public.setPlaceholderText(QCoreApplication.translate("FicheSequence", u"Affich\u00e9 \u00e0 la place de l'artiste et du titre masqu\u00e9s ; facultatif", None))
        self.etiquette_masquage.setText(QCoreApplication.translate("FicheSequence", u"&Artiste et titre", None))
        self.groupe_elements.setTitle(QCoreApplication.translate("FicheSequence", u"\u00c9l\u00e9ments, dans l'ordre de passage", None))
        ___qtreewidgetitem = self.elements.headerItem()
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("FicheSequence", u"D\u00e9tail", None))
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("FicheSequence", u"\u00c9l\u00e9ment", None))
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("FicheSequence", u"Genre", None))
        self.ajouter_sonores.setText(QCoreApplication.translate("FicheSequence", u"\u2795 Ajouter des sonores\u2026", None))
        self.ajouter_banques.setText(QCoreApplication.translate("FicheSequence", u"\u2795 Ajouter des banques\u2026", None))
        self.retirer_element.setText(QCoreApplication.translate("FicheSequence", u"\u2796 Retirer l'\u00e9l\u00e9ment", None))
        self.monter.setText(QCoreApplication.translate("FicheSequence", u"Monter", None))
        self.descendre.setText(QCoreApplication.translate("FicheSequence", u"Descendre", None))
        self.groupe_evenements.setTitle(QCoreApplication.translate("FicheSequence", u"\u00c9v\u00e9nements o\u00f9 elle figure", None))
        self.explication_evenements.setText(QCoreApplication.translate("FicheSequence", u"Une s\u00e9quence se place dans un \u00e9v\u00e9nement depuis la fiche de l'\u00e9v\u00e9nement.", None))
        self.supprimer.setText(QCoreApplication.translate("FicheSequence", u"\u274c Supprimer\u2026", None))
#if QT_CONFIG(tooltip)
        self.supprimer.setToolTip(QCoreApplication.translate("FicheSequence", u"Supprime l'\u00e9l\u00e9ment de la base, apr\u00e8s confirmation ; aucun fichier n'est touch\u00e9.", None))
#endif // QT_CONFIG(tooltip)
        self.dupliquer.setText(QCoreApplication.translate("FicheSequence", u"Dupliquer", None))
#if QT_CONFIG(tooltip)
        self.dupliquer.setToolTip(QCoreApplication.translate("FicheSequence", u"Ouvre une copie de l'\u00e9l\u00e9ment dans une nouvelle fiche ; rien n'est enregistr\u00e9 avant \u00ab Enregistrer \u00bb.", None))
#endif // QT_CONFIG(tooltip)
        self.annuler.setText(QCoreApplication.translate("FicheSequence", u"Annuler", None))
        self.enregistrer.setText(QCoreApplication.translate("FicheSequence", u"Enregistrer", None))
        pass
    # retranslateUi

