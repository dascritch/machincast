# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'fenetre_principale.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QMainWindow, QPushButton,
    QSizePolicy, QSpacerItem, QStatusBar, QTabWidget,
    QVBoxLayout, QWidget)

class Ui_FenetrePrincipale(object):
    def setupUi(self, FenetrePrincipale):
        if not FenetrePrincipale.objectName():
            FenetrePrincipale.setObjectName(u"FenetrePrincipale")
        FenetrePrincipale.resize(1100, 800)
        self.centre = QWidget(FenetrePrincipale)
        self.centre.setObjectName(u"centre")
        self.disposition = QVBoxLayout(self.centre)
        self.disposition.setObjectName(u"disposition")
        self.onglets = QTabWidget(self.centre)
        self.onglets.setObjectName(u"onglets")
        self.onglets.setDocumentMode(True)

        self.disposition.addWidget(self.onglets)

        self.pied = QHBoxLayout()
        self.pied.setObjectName(u"pied")
        self.preecouter_l_antenne = QPushButton(self.centre)
        self.preecouter_l_antenne.setObjectName(u"preecouter_l_antenne")

        self.pied.addWidget(self.preecouter_l_antenne)

        self.pousser_le_pied = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.pied.addItem(self.pousser_le_pied)


        self.disposition.addLayout(self.pied)

        FenetrePrincipale.setCentralWidget(self.centre)
        self.barre_d_etat = QStatusBar(FenetrePrincipale)
        self.barre_d_etat.setObjectName(u"barre_d_etat")
        FenetrePrincipale.setStatusBar(self.barre_d_etat)

        self.retranslateUi(FenetrePrincipale)

        QMetaObject.connectSlotsByName(FenetrePrincipale)
    # setupUi

    def retranslateUi(self, FenetrePrincipale):
        FenetrePrincipale.setWindowTitle(QCoreApplication.translate("FenetrePrincipale", u"MachinCast", None))
#if QT_CONFIG(tooltip)
        self.preecouter_l_antenne.setToolTip(QCoreApplication.translate("FenetrePrincipale", u"\u00c9couter l'antenne sur la sortie de pr\u00e9-\u00e9coute, aussit\u00f4t", None))
#endif // QT_CONFIG(tooltip)
        self.preecouter_l_antenne.setText(QCoreApplication.translate("FenetrePrincipale", u"Pr\u00e9-\u00e9coute", None))
    # retranslateUi

