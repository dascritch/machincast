# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'choix.ui'
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

class Ui_Choix(object):
    def setupUi(self, Choix):
        if not Choix.objectName():
            Choix.setObjectName(u"Choix")
        Choix.resize(1000, 600)
        self.disposition = QVBoxLayout(Choix)
        self.disposition.setObjectName(u"disposition")
        self.explication = QLabel(Choix)
        self.explication.setObjectName(u"explication")
        self.explication.setWordWrap(True)

        self.disposition.addWidget(self.explication)

        self.boutons = QDialogButtonBox(Choix)
        self.boutons.setObjectName(u"boutons")
        self.boutons.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.disposition.addWidget(self.boutons)


        self.retranslateUi(Choix)

        QMetaObject.connectSlotsByName(Choix)
    # setupUi

    def retranslateUi(self, Choix):
        Choix.setWindowTitle(QCoreApplication.translate("Choix", u"Ajouter", None))
        self.explication.setText("")
    # retranslateUi

