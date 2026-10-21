# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'suggestions.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QApplication, QCheckBox,
    QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QLabel, QListWidget, QListWidgetItem,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_FenetreSuggestions(object):
    def setupUi(self, FenetreSuggestions):
        if not FenetreSuggestions.objectName():
            FenetreSuggestions.setObjectName(u"FenetreSuggestions")
        FenetreSuggestions.setModal(True)
        self.disposition = QVBoxLayout(FenetreSuggestions)
        self.disposition.setObjectName(u"disposition")
        self.explication = QLabel(FenetreSuggestions)
        self.explication.setObjectName(u"explication")
        self.explication.setWordWrap(True)

        self.disposition.addWidget(self.explication)

        self.elements = QListWidget(FenetreSuggestions)
        self.elements.setObjectName(u"elements")
        self.elements.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        self.disposition.addWidget(self.elements)

        self.groupe_antenne = QGroupBox(FenetreSuggestions)
        self.groupe_antenne.setObjectName(u"groupe_antenne")
        self.formulaire_antenne = QFormLayout(self.groupe_antenne)
        self.formulaire_antenne.setObjectName(u"formulaire_antenne")
        self.etiquette_antenne = QLabel(self.groupe_antenne)
        self.etiquette_antenne.setObjectName(u"etiquette_antenne")

        self.formulaire_antenne.setWidget(0, QFormLayout.ItemRole.LabelRole, self.etiquette_antenne)

        self.antenne = QComboBox(self.groupe_antenne)
        self.antenne.setObjectName(u"antenne")

        self.formulaire_antenne.setWidget(0, QFormLayout.ItemRole.FieldRole, self.antenne)


        self.disposition.addWidget(self.groupe_antenne)

        self.ne_plus_proposer = QCheckBox(FenetreSuggestions)
        self.ne_plus_proposer.setObjectName(u"ne_plus_proposer")

        self.disposition.addWidget(self.ne_plus_proposer)

        self.boutons = QDialogButtonBox(FenetreSuggestions)
        self.boutons.setObjectName(u"boutons")
        self.boutons.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.disposition.addWidget(self.boutons)

#if QT_CONFIG(shortcut)
        self.etiquette_antenne.setBuddy(self.antenne)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(FenetreSuggestions)

        QMetaObject.connectSlotsByName(FenetreSuggestions)
    # setupUi

    def retranslateUi(self, FenetreSuggestions):
        FenetreSuggestions.setWindowTitle(QCoreApplication.translate("FenetreSuggestions", u"Pour bien d\u00e9marrer", None))
        self.explication.setText(QCoreApplication.translate("FenetreSuggestions", u"Il manque de quoi d\u00e9marrer l'antenne. Cochez ce que MachinCast doit cr\u00e9er : les banques restent \u00e0 remplir, depuis leur fiche ou par l'indexation de leurs r\u00e9pertoires.", None))
        self.groupe_antenne.setTitle(QCoreApplication.translate("FenetreSuggestions", u"Sortie audio de la diffusion", None))
        self.etiquette_antenne.setText(QCoreApplication.translate("FenetreSuggestions", u"&Antenne", None))
#if QT_CONFIG(tooltip)
        self.antenne.setToolTip(QCoreApplication.translate("FenetreSuggestions", u"Le p\u00e9riph\u00e9rique sur lequel Machin lecture diffuse l'antenne : sans lui, il refuse de diffuser", None))
#endif // QT_CONFIG(tooltip)
        self.ne_plus_proposer.setText(QCoreApplication.translate("FenetreSuggestions", u"&Ne plus proposer au lancement", None))
    # retranslateUi

