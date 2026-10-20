# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'fiche_evenement.ui'
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
    QDateTimeEdit, QFormLayout, QGridLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QSpacerItem, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget)

class Ui_FicheEvenement(object):
    def setupUi(self, FicheEvenement):
        if not FicheEvenement.objectName():
            FicheEvenement.setObjectName(u"FicheEvenement")
        FicheEvenement.resize(1100, 700)
        self.disposition = QVBoxLayout(FicheEvenement)
        self.disposition.setObjectName(u"disposition")
        self.haut = QHBoxLayout()
        self.haut.setObjectName(u"haut")
        self.formulaire = QFormLayout()
        self.formulaire.setObjectName(u"formulaire")
        self.etiquette_nom_interne = QLabel(FicheEvenement)
        self.etiquette_nom_interne.setObjectName(u"etiquette_nom_interne")

        self.formulaire.setWidget(0, QFormLayout.ItemRole.LabelRole, self.etiquette_nom_interne)

        self.nom_interne = QLineEdit(FicheEvenement)
        self.nom_interne.setObjectName(u"nom_interne")
        self.nom_interne.setMaxLength(255)

        self.formulaire.setWidget(0, QFormLayout.ItemRole.FieldRole, self.nom_interne)

        self.etiquette_nom_public = QLabel(FicheEvenement)
        self.etiquette_nom_public.setObjectName(u"etiquette_nom_public")

        self.formulaire.setWidget(1, QFormLayout.ItemRole.LabelRole, self.etiquette_nom_public)

        self.nom_public = QLineEdit(FicheEvenement)
        self.nom_public.setObjectName(u"nom_public")
        self.nom_public.setMaxLength(255)

        self.formulaire.setWidget(1, QFormLayout.ItemRole.FieldRole, self.nom_public)

        self.etiquette_priorite = QLabel(FicheEvenement)
        self.etiquette_priorite.setObjectName(u"etiquette_priorite")

        self.formulaire.setWidget(2, QFormLayout.ItemRole.LabelRole, self.etiquette_priorite)

        self.priorite = QComboBox(FicheEvenement)
        self.priorite.setObjectName(u"priorite")

        self.formulaire.setWidget(2, QFormLayout.ItemRole.FieldRole, self.priorite)

        self.etiquette_masquage = QLabel(FicheEvenement)
        self.etiquette_masquage.setObjectName(u"etiquette_masquage")

        self.formulaire.setWidget(3, QFormLayout.ItemRole.LabelRole, self.etiquette_masquage)

        self.masquage = QComboBox(FicheEvenement)
        self.masquage.setObjectName(u"masquage")

        self.formulaire.setWidget(3, QFormLayout.ItemRole.FieldRole, self.masquage)


        self.haut.addLayout(self.formulaire)

        self.groupe_grille = QGroupBox(FicheEvenement)
        self.groupe_grille.setObjectName(u"groupe_grille")
        self.disposition_grille = QGridLayout(self.groupe_grille)
        self.disposition_grille.setObjectName(u"disposition_grille")
        self.a_debut = QCheckBox(self.groupe_grille)
        self.a_debut.setObjectName(u"a_debut")

        self.disposition_grille.addWidget(self.a_debut, 0, 0, 1, 1)

        self.debut = QDateTimeEdit(self.groupe_grille)
        self.debut.setObjectName(u"debut")
        self.debut.setEnabled(False)
        self.debut.setCalendarPopup(True)

        self.disposition_grille.addWidget(self.debut, 0, 1, 1, 1)

        self.a_fin = QCheckBox(self.groupe_grille)
        self.a_fin.setObjectName(u"a_fin")

        self.disposition_grille.addWidget(self.a_fin, 1, 0, 1, 1)

        self.fin = QDateTimeEdit(self.groupe_grille)
        self.fin.setObjectName(u"fin")
        self.fin.setEnabled(False)
        self.fin.setCalendarPopup(True)

        self.disposition_grille.addWidget(self.fin, 1, 1, 1, 1)

        self.disposition_jours = QHBoxLayout()
        self.disposition_jours.setObjectName(u"disposition_jours")
        self.lundi = QCheckBox(self.groupe_grille)
        self.lundi.setObjectName(u"lundi")

        self.disposition_jours.addWidget(self.lundi)

        self.mardi = QCheckBox(self.groupe_grille)
        self.mardi.setObjectName(u"mardi")

        self.disposition_jours.addWidget(self.mardi)

        self.mercredi = QCheckBox(self.groupe_grille)
        self.mercredi.setObjectName(u"mercredi")

        self.disposition_jours.addWidget(self.mercredi)

        self.jeudi = QCheckBox(self.groupe_grille)
        self.jeudi.setObjectName(u"jeudi")

        self.disposition_jours.addWidget(self.jeudi)

        self.vendredi = QCheckBox(self.groupe_grille)
        self.vendredi.setObjectName(u"vendredi")

        self.disposition_jours.addWidget(self.vendredi)

        self.samedi = QCheckBox(self.groupe_grille)
        self.samedi.setObjectName(u"samedi")

        self.disposition_jours.addWidget(self.samedi)

        self.dimanche = QCheckBox(self.groupe_grille)
        self.dimanche.setObjectName(u"dimanche")

        self.disposition_jours.addWidget(self.dimanche)


        self.disposition_grille.addLayout(self.disposition_jours, 2, 0, 1, 2)

        self.explication_grille = QLabel(self.groupe_grille)
        self.explication_grille.setObjectName(u"explication_grille")
        self.explication_grille.setWordWrap(True)

        self.disposition_grille.addWidget(self.explication_grille, 3, 0, 1, 2)


        self.haut.addWidget(self.groupe_grille)

        self.haut.setStretch(0, 1)
        self.haut.setStretch(1, 1)

        self.disposition.addLayout(self.haut)

        self.listes = QHBoxLayout()
        self.listes.setObjectName(u"listes")
        self.groupe_elements = QGroupBox(FicheEvenement)
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

        self.ajouter_sequences = QPushButton(self.groupe_elements)
        self.ajouter_sequences.setObjectName(u"ajouter_sequences")

        self.boutons_elements.addWidget(self.ajouter_sequences)

        self.ajouter_marques_pages = QPushButton(self.groupe_elements)
        self.ajouter_marques_pages.setObjectName(u"ajouter_marques_pages")

        self.boutons_elements.addWidget(self.ajouter_marques_pages)

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


        self.disposition.addLayout(self.listes)

        self.pied = QHBoxLayout()
        self.pied.setObjectName(u"pied")
        self.supprimer = QPushButton(FicheEvenement)
        self.supprimer.setObjectName(u"supprimer")

        self.pied.addWidget(self.supprimer)

        self.message = QLabel(FicheEvenement)
        self.message.setObjectName(u"message")
        self.message.setWordWrap(True)

        self.pied.addWidget(self.message)

        self.annuler = QPushButton(FicheEvenement)
        self.annuler.setObjectName(u"annuler")

        self.pied.addWidget(self.annuler)

        self.enregistrer = QPushButton(FicheEvenement)
        self.enregistrer.setObjectName(u"enregistrer")

        self.pied.addWidget(self.enregistrer)

        self.pied.setStretch(1, 1)

        self.disposition.addLayout(self.pied)

        self.disposition.setStretch(1, 1)
#if QT_CONFIG(shortcut)
        self.etiquette_nom_interne.setBuddy(self.nom_interne)
        self.etiquette_nom_public.setBuddy(self.nom_public)
        self.etiquette_priorite.setBuddy(self.priorite)
        self.etiquette_masquage.setBuddy(self.masquage)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(FicheEvenement)

        self.enregistrer.setDefault(True)


        QMetaObject.connectSlotsByName(FicheEvenement)
    # setupUi

    def retranslateUi(self, FicheEvenement):
        self.etiquette_nom_interne.setText(QCoreApplication.translate("FicheEvenement", u"&Nom interne", None))
        self.nom_interne.setPlaceholderText(QCoreApplication.translate("FicheEvenement", u"Obligatoire, et propre \u00e0 cet \u00e9v\u00e9nement", None))
        self.etiquette_nom_public.setText(QCoreApplication.translate("FicheEvenement", u"Nom &public", None))
        self.nom_public.setPlaceholderText(QCoreApplication.translate("FicheEvenement", u"Affich\u00e9 \u00e0 la place de l'artiste et du titre masqu\u00e9s ; facultatif", None))
        self.etiquette_priorite.setText(QCoreApplication.translate("FicheEvenement", u"P&riorit\u00e9", None))
        self.etiquette_masquage.setText(QCoreApplication.translate("FicheEvenement", u"&Artiste et titre", None))
        self.groupe_grille.setTitle(QCoreApplication.translate("FicheEvenement", u"Grille : premi\u00e8re occurrence, et jours o\u00f9 elle revient", None))
        self.a_debut.setText(QCoreApplication.translate("FicheEvenement", u"&D\u00e9but", None))
        self.debut.setDisplayFormat(QCoreApplication.translate("FicheEvenement", u"dd/MM/yyyy HH:mm", None))
        self.a_fin.setText(QCoreApplication.translate("FicheEvenement", u"&Fin", None))
        self.fin.setDisplayFormat(QCoreApplication.translate("FicheEvenement", u"dd/MM/yyyy HH:mm", None))
        self.lundi.setText(QCoreApplication.translate("FicheEvenement", u"lundi", None))
        self.mardi.setText(QCoreApplication.translate("FicheEvenement", u"mardi", None))
        self.mercredi.setText(QCoreApplication.translate("FicheEvenement", u"mercredi", None))
        self.jeudi.setText(QCoreApplication.translate("FicheEvenement", u"jeudi", None))
        self.vendredi.setText(QCoreApplication.translate("FicheEvenement", u"vendredi", None))
        self.samedi.setText(QCoreApplication.translate("FicheEvenement", u"samedi", None))
        self.dimanche.setText(QCoreApplication.translate("FicheEvenement", u"dimanche", None))
        self.explication_grille.setText(QCoreApplication.translate("FicheEvenement", u"Sans jour coch\u00e9, l'\u00e9v\u00e9nement n'a qu'une occurrence. Sans fin, une \u00e9mission ou un sp\u00e9cial dure jusqu'au bout de sa liste ; un fil musical sans d\u00e9but est permanent, et sert de fond.", None))
        self.groupe_elements.setTitle(QCoreApplication.translate("FicheEvenement", u"Liste de lecture, dans l'ordre de passage", None))
        ___qtreewidgetitem = self.elements.headerItem()
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("FicheEvenement", u"D\u00e9tail", None))
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("FicheEvenement", u"\u00c9l\u00e9ment", None))
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("FicheEvenement", u"Genre", None))
        self.ajouter_sonores.setText(QCoreApplication.translate("FicheEvenement", u"Ajouter des sonores\u2026", None))
        self.ajouter_banques.setText(QCoreApplication.translate("FicheEvenement", u"Ajouter des banques\u2026", None))
        self.ajouter_sequences.setText(QCoreApplication.translate("FicheEvenement", u"Ajouter des s\u00e9quences\u2026", None))
#if QT_CONFIG(tooltip)
        self.ajouter_marques_pages.setToolTip(QCoreApplication.translate("FicheEvenement", u"Ajoute le stream qui suit chaque marque-page choisi, ou en cr\u00e9e un \u00e0 l'enregistrement", None))
#endif // QT_CONFIG(tooltip)
        self.ajouter_marques_pages.setText(QCoreApplication.translate("FicheEvenement", u"Ajouter des marques-pages\u2026", None))
        self.retirer_element.setText(QCoreApplication.translate("FicheEvenement", u"Retirer l'\u00e9l\u00e9ment", None))
        self.monter.setText(QCoreApplication.translate("FicheEvenement", u"Monter", None))
        self.descendre.setText(QCoreApplication.translate("FicheEvenement", u"Descendre", None))
        self.supprimer.setText(QCoreApplication.translate("FicheEvenement", u"Supprimer\u2026", None))
#if QT_CONFIG(tooltip)
        self.supprimer.setToolTip(QCoreApplication.translate("FicheEvenement", u"Supprime l'\u00e9l\u00e9ment de la base, apr\u00e8s confirmation ; aucun fichier n'est touch\u00e9.", None))
#endif // QT_CONFIG(tooltip)
        self.annuler.setText(QCoreApplication.translate("FicheEvenement", u"Annuler", None))
        self.enregistrer.setText(QCoreApplication.translate("FicheEvenement", u"Enregistrer", None))
        pass
    # retranslateUi

