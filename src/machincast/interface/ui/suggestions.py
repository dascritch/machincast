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

class Ui_SuggestionsWindow(object):
    def setupUi(self, SuggestionsWindow):
        if not SuggestionsWindow.objectName():
            SuggestionsWindow.setObjectName(u"SuggestionsWindow")
        SuggestionsWindow.setModal(True)
        self.arrangement = QVBoxLayout(SuggestionsWindow)
        self.arrangement.setObjectName(u"arrangement")
        self.sound_cards_group = QGroupBox(SuggestionsWindow)
        self.sound_cards_group.setObjectName(u"sound_cards_group")
        self.sound_cards_layout = QVBoxLayout(self.sound_cards_group)
        self.sound_cards_layout.setObjectName(u"sound_cards_layout")
        self.sound_cards_explanation = QLabel(self.sound_cards_group)
        self.sound_cards_explanation.setObjectName(u"sound_cards_explanation")
        self.sound_cards_explanation.setWordWrap(True)

        self.sound_cards_layout.addWidget(self.sound_cards_explanation)


        self.arrangement.addWidget(self.sound_cards_group)

        self.explanation = QLabel(SuggestionsWindow)
        self.explanation.setObjectName(u"explanation")
        self.explanation.setWordWrap(True)

        self.arrangement.addWidget(self.explanation)

        self.items = QListWidget(SuggestionsWindow)
        self.items.setObjectName(u"items")
        self.items.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        self.arrangement.addWidget(self.items)

        self.more_offer = QCheckBox(SuggestionsWindow)
        self.more_offer.setObjectName(u"more_offer")

        self.arrangement.addWidget(self.more_offer)

        self.buttons = QDialogButtonBox(SuggestionsWindow)
        self.buttons.setObjectName(u"buttons")
        self.buttons.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.arrangement.addWidget(self.buttons)


        self.retranslateUi(SuggestionsWindow)

        QMetaObject.connectSlotsByName(SuggestionsWindow)
    # setupUi

    def retranslateUi(self, SuggestionsWindow):
        SuggestionsWindow.setWindowTitle(QCoreApplication.translate("SuggestionsWindow", u"Pour bien d\u00e9marrer", None))
        self.sound_cards_group.setTitle(QCoreApplication.translate("SuggestionsWindow", u"Cartes son", None))
        self.sound_cards_explanation.setText(QCoreApplication.translate("SuggestionsWindow", u"Choisissez d'abord la carte son de l'antenne, puis celle de la pr\u00e9-\u00e9coute. \u00ab Tester \u00bb joue 2 secondes de son de test sur la carte de sa ligne : sur celle de l'antenne, il part \u00e0 l'antenne.", None))
        self.explanation.setText(QCoreApplication.translate("SuggestionsWindow", u"Il manque de quoi d\u00e9marrer l'antenne. Cochez ce que MachinCast doit cr\u00e9er : les banques restent \u00e0 remplir, depuis leur fiche ou par l'indexation de leurs r\u00e9pertoires.", None))
        self.more_offer.setText(QCoreApplication.translate("SuggestionsWindow", u"&Ne plus proposer au lancement", None))
    # retranslateUi

