# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'choix_sonores.ui'
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

class Ui_ChoixSonores(object):
    def setupUi(self, ChoixSonores):
        if not ChoixSonores.objectName():
            ChoixSonores.setObjectName(u"ChoixSonores")
        ChoixSonores.resize(1000, 600)
        self.disposition = QVBoxLayout(ChoixSonores)
        self.disposition.setObjectName(u"disposition")
        self.explication = QLabel(ChoixSonores)
        self.explication.setObjectName(u"explication")
        self.explication.setWordWrap(True)

        self.disposition.addWidget(self.explication)

        self.boutons = QDialogButtonBox(ChoixSonores)
        self.boutons.setObjectName(u"boutons")
        self.boutons.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.disposition.addWidget(self.boutons)


        self.retranslateUi(ChoixSonores)

        QMetaObject.connectSlotsByName(ChoixSonores)
    # setupUi

    def retranslateUi(self, ChoixSonores):
        ChoixSonores.setWindowTitle(QCoreApplication.translate("ChoixSonores", u"Ajouter des sonores \u00e0 la banque", None))
        self.explication.setText(QCoreApplication.translate("ChoixSonores", u"Choisir un ou plusieurs sonores d\u00e9j\u00e0 en base (Ctrl ou Maj pour en prendre plusieurs). Un sonore qui est d\u00e9j\u00e0 dans la banque n'y est pas ajout\u00e9 une seconde fois.", None))
    # retranslateUi

