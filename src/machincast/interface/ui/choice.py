# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'choice.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QLabel, QSizePolicy, QVBoxLayout, QWidget)

class Ui_Choice(object):
    def setupUi(self, Choice):
        if not Choice.objectName():
            Choice.setObjectName(u"Choice")
        Choice.resize(1000, 600)
        self.arrangement = QVBoxLayout(Choice)
        self.arrangement.setObjectName(u"arrangement")
        self.explanation = QLabel(Choice)
        self.explanation.setObjectName(u"explanation")
        self.explanation.setWordWrap(True)

        self.arrangement.addWidget(self.explanation)

        self.buttons = QDialogButtonBox(Choice)
        self.buttons.setObjectName(u"buttons")
        self.buttons.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.arrangement.addWidget(self.buttons)


        self.retranslateUi(Choice)

        QMetaObject.connectSlotsByName(Choice)
    # setupUi

    def retranslateUi(self, Choice):
        Choice.setWindowTitle(QCoreApplication.translate("Choice", u"Ajouter", None))
        self.explanation.setText("")
    # retranslateUi

