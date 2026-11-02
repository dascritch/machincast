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
    QDialog, QDialogButtonBox, QGroupBox, QLabel,
    QListWidget, QListWidgetItem, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_FenetreSuggestions(object):
    def setupUi(self, FenetreSuggestions):
        if not FenetreSuggestions.objectName():
            FenetreSuggestions.setObjectName(u"FenetreSuggestions")
        FenetreSuggestions.setModal(True)
        self.disposition = QVBoxLayout(FenetreSuggestions)
        self.disposition.setObjectName(u"disposition")
        self.groupe_cartes_son = QGroupBox(FenetreSuggestions)
        self.groupe_cartes_son.setObjectName(u"groupe_cartes_son")
        self.disposition_cartes_son = QVBoxLayout(self.groupe_cartes_son)
        self.disposition_cartes_son.setObjectName(u"disposition_cartes_son")
        self.explication_cartes_son = QLabel(self.groupe_cartes_son)
        self.explication_cartes_son.setObjectName(u"explication_cartes_son")
        self.explication_cartes_son.setWordWrap(True)

        self.disposition_cartes_son.addWidget(self.explication_cartes_son)


        self.disposition.addWidget(self.groupe_cartes_son)

        self.explication = QLabel(FenetreSuggestions)
        self.explication.setObjectName(u"explication")
        self.explication.setWordWrap(True)

        self.disposition.addWidget(self.explication)

        self.elements = QListWidget(FenetreSuggestions)
        self.elements.setObjectName(u"elements")
        self.elements.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        self.disposition.addWidget(self.elements)

        self.ne_plus_proposer = QCheckBox(FenetreSuggestions)
        self.ne_plus_proposer.setObjectName(u"ne_plus_proposer")

        self.disposition.addWidget(self.ne_plus_proposer)

        self.boutons = QDialogButtonBox(FenetreSuggestions)
        self.boutons.setObjectName(u"boutons")
        self.boutons.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.disposition.addWidget(self.boutons)


        self.retranslateUi(FenetreSuggestions)

        QMetaObject.connectSlotsByName(FenetreSuggestions)
    # setupUi

    def retranslateUi(self, FenetreSuggestions):
        FenetreSuggestions.setWindowTitle(QCoreApplication.translate("FenetreSuggestions", u"Pour bien d\u00e9marrer", None))
        self.groupe_cartes_son.setTitle(QCoreApplication.translate("FenetreSuggestions", u"Cartes son", None))
        self.explication_cartes_son.setText(QCoreApplication.translate("FenetreSuggestions", u"Choisissez d'abord la carte son de l'antenne, puis celle de la pr\u00e9-\u00e9coute. \u00ab Tester \u00bb joue 2 secondes de son de test sur la carte de sa ligne : sur celle de l'antenne, il part \u00e0 l'antenne.", None))
        self.explication.setText(QCoreApplication.translate("FenetreSuggestions", u"Il manque de quoi d\u00e9marrer l'antenne. Cochez ce que MachinCast doit cr\u00e9er : les banques restent \u00e0 remplir, depuis leur fiche ou par l'indexation de leurs r\u00e9pertoires.", None))
        self.ne_plus_proposer.setText(QCoreApplication.translate("FenetreSuggestions", u"&Ne plus proposer au lancement", None))
    # retranslateUi

