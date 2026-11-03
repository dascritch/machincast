# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'cartes_son.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFormLayout, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QWidget)

class Ui_CartesSon(object):
    def setupUi(self, CartesSon):
        if not CartesSon.objectName():
            CartesSon.setObjectName(u"CartesSon")
        self.formulaire = QFormLayout(CartesSon)
        self.formulaire.setObjectName(u"formulaire")
        self.formulaire.setContentsMargins(0, 0, 0, 0)
        self.etiquette_sortie = QLabel(CartesSon)
        self.etiquette_sortie.setObjectName(u"etiquette_sortie")

        self.formulaire.setWidget(0, QFormLayout.ItemRole.LabelRole, self.etiquette_sortie)

        self.sortie = QComboBox(CartesSon)
        self.sortie.setObjectName(u"sortie")

        self.formulaire.setWidget(0, QFormLayout.ItemRole.FieldRole, self.sortie)

        self.etiquette_antenne = QLabel(CartesSon)
        self.etiquette_antenne.setObjectName(u"etiquette_antenne")

        self.formulaire.setWidget(1, QFormLayout.ItemRole.LabelRole, self.etiquette_antenne)

        self.ligne_antenne = QHBoxLayout()
        self.ligne_antenne.setObjectName(u"ligne_antenne")
        self.antenne = QComboBox(CartesSon)
        self.antenne.setObjectName(u"antenne")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.antenne.sizePolicy().hasHeightForWidth())
        self.antenne.setSizePolicy(sizePolicy)

        self.ligne_antenne.addWidget(self.antenne)

        self.tester_antenne = QPushButton(CartesSon)
        self.tester_antenne.setObjectName(u"tester_antenne")

        self.ligne_antenne.addWidget(self.tester_antenne)


        self.formulaire.setLayout(1, QFormLayout.ItemRole.FieldRole, self.ligne_antenne)

        self.etiquette_preecoute = QLabel(CartesSon)
        self.etiquette_preecoute.setObjectName(u"etiquette_preecoute")

        self.formulaire.setWidget(2, QFormLayout.ItemRole.LabelRole, self.etiquette_preecoute)

        self.ligne_preecoute = QHBoxLayout()
        self.ligne_preecoute.setObjectName(u"ligne_preecoute")
        self.preecoute = QComboBox(CartesSon)
        self.preecoute.setObjectName(u"preecoute")
        sizePolicy.setHeightForWidth(self.preecoute.sizePolicy().hasHeightForWidth())
        self.preecoute.setSizePolicy(sizePolicy)

        self.ligne_preecoute.addWidget(self.preecoute)

        self.tester_preecoute = QPushButton(CartesSon)
        self.tester_preecoute.setObjectName(u"tester_preecoute")

        self.ligne_preecoute.addWidget(self.tester_preecoute)


        self.formulaire.setLayout(2, QFormLayout.ItemRole.FieldRole, self.ligne_preecoute)

        self.essai = QLabel(CartesSon)
        self.essai.setObjectName(u"essai")
        self.essai.setWordWrap(True)

        self.formulaire.setWidget(3, QFormLayout.ItemRole.SpanningRole, self.essai)

#if QT_CONFIG(shortcut)
        self.etiquette_sortie.setBuddy(self.sortie)
        self.etiquette_antenne.setBuddy(self.antenne)
        self.etiquette_preecoute.setBuddy(self.preecoute)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(CartesSon)

        QMetaObject.connectSlotsByName(CartesSon)
    # setupUi

    def retranslateUi(self, CartesSon):
        self.etiquette_sortie.setText(QCoreApplication.translate("CartesSon", u"&Type de sortie", None))
#if QT_CONFIG(tooltip)
        self.sortie.setToolTip(QCoreApplication.translate("CartesSon", u"Le serveur audio par lequel passent l'antenne et la pr\u00e9-\u00e9coute", None))
#endif // QT_CONFIG(tooltip)
        self.etiquette_antenne.setText(QCoreApplication.translate("CartesSon", u"&Antenne", None))
#if QT_CONFIG(tooltip)
        self.antenne.setToolTip(QCoreApplication.translate("CartesSon", u"La carte son sur laquelle Machin player diffuse l'antenne", None))
#endif // QT_CONFIG(tooltip)
        self.tester_antenne.setText(QCoreApplication.translate("CartesSon", u"Tester", None))
        self.etiquette_preecoute.setText(QCoreApplication.translate("CartesSon", u"&Pr\u00e9-\u00e9coute", None))
#if QT_CONFIG(tooltip)
        self.preecoute.setToolTip(QCoreApplication.translate("CartesSon", u"La carte son de la pr\u00e9-\u00e9coute de l'interface, jamais celle de l'antenne", None))
#endif // QT_CONFIG(tooltip)
        self.tester_preecoute.setText(QCoreApplication.translate("CartesSon", u"Tester", None))
        pass
    # retranslateUi

