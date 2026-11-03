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
        SuggestionsWindow.setWindowTitle(QCoreApplication.translate("SuggestionsWindow", u"Getting started", None))
        self.sound_cards_group.setTitle(QCoreApplication.translate("SuggestionsWindow", u"Sound cards", None))
        self.sound_cards_explanation.setText(QCoreApplication.translate("SuggestionsWindow", u"First choose the on-air sound card, then the pre-listen one. \u201cTest\u201d plays 2 seconds of test sound on the card of its line: on the on-air one, it goes on air.", None))
        self.explanation.setText(QCoreApplication.translate("SuggestionsWindow", u"Something is missing to start the on-air output. Tick what MachinCast must create: the banks remain to be filled, from their card or by the indexing of their directories.", None))
        self.more_offer.setText(QCoreApplication.translate("SuggestionsWindow", u"&Do not offer at launch again", None))
    # retranslateUi

