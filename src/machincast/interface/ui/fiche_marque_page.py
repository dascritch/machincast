# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'fiche_marque_page.ui'
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
from PySide6.QtWidgets import (QApplication, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget)

class Ui_FicheMarquePage(object):
    def setupUi(self, FicheMarquePage):
        if not FicheMarquePage.objectName():
            FicheMarquePage.setObjectName(u"FicheMarquePage")
        FicheMarquePage.resize(900, 600)
        self.disposition = QVBoxLayout(FicheMarquePage)
        self.disposition.setObjectName(u"disposition")
        self.formulaire = QFormLayout()
        self.formulaire.setObjectName(u"formulaire")
        self.etiquette_nom = QLabel(FicheMarquePage)
        self.etiquette_nom.setObjectName(u"etiquette_nom")

        self.formulaire.setWidget(0, QFormLayout.ItemRole.LabelRole, self.etiquette_nom)

        self.nom = QLineEdit(FicheMarquePage)
        self.nom.setObjectName(u"nom")
        self.nom.setMaxLength(255)

        self.formulaire.setWidget(0, QFormLayout.ItemRole.FieldRole, self.nom)

        self.etiquette_url = QLabel(FicheMarquePage)
        self.etiquette_url.setObjectName(u"etiquette_url")

        self.formulaire.setWidget(1, QFormLayout.ItemRole.LabelRole, self.etiquette_url)

        self.url = QLineEdit(FicheMarquePage)
        self.url.setObjectName(u"url")

        self.formulaire.setWidget(1, QFormLayout.ItemRole.FieldRole, self.url)


        self.disposition.addLayout(self.formulaire)

        self.essai = QHBoxLayout()
        self.essai.setObjectName(u"essai")
        self.tester = QPushButton(FicheMarquePage)
        self.tester.setObjectName(u"tester")

        self.essai.addWidget(self.tester)

        self.resultat_essai = QLabel(FicheMarquePage)
        self.resultat_essai.setObjectName(u"resultat_essai")
        self.resultat_essai.setWordWrap(True)

        self.essai.addWidget(self.resultat_essai)

        self.essai.setStretch(1, 1)

        self.disposition.addLayout(self.essai)

        self.groupe_streams = QGroupBox(FicheMarquePage)
        self.groupe_streams.setObjectName(u"groupe_streams")
        self.disposition_streams = QVBoxLayout(self.groupe_streams)
        self.disposition_streams.setObjectName(u"disposition_streams")
        self.streams = QListWidget(self.groupe_streams)
        self.streams.setObjectName(u"streams")
        self.streams.setAlternatingRowColors(True)

        self.disposition_streams.addWidget(self.streams)

        self.explication_streams = QLabel(self.groupe_streams)
        self.explication_streams.setObjectName(u"explication_streams")
        self.explication_streams.setWordWrap(True)

        self.disposition_streams.addWidget(self.explication_streams)


        self.disposition.addWidget(self.groupe_streams)

        self.pied = QHBoxLayout()
        self.pied.setObjectName(u"pied")
        self.supprimer = QPushButton(FicheMarquePage)
        self.supprimer.setObjectName(u"supprimer")

        self.pied.addWidget(self.supprimer)

        self.message = QLabel(FicheMarquePage)
        self.message.setObjectName(u"message")
        self.message.setWordWrap(True)

        self.pied.addWidget(self.message)

        self.annuler = QPushButton(FicheMarquePage)
        self.annuler.setObjectName(u"annuler")

        self.pied.addWidget(self.annuler)

        self.enregistrer = QPushButton(FicheMarquePage)
        self.enregistrer.setObjectName(u"enregistrer")

        self.pied.addWidget(self.enregistrer)

        self.pied.setStretch(1, 1)

        self.disposition.addLayout(self.pied)

        self.disposition.setStretch(2, 1)
#if QT_CONFIG(shortcut)
        self.etiquette_nom.setBuddy(self.nom)
        self.etiquette_url.setBuddy(self.url)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(FicheMarquePage)

        self.enregistrer.setDefault(True)


        QMetaObject.connectSlotsByName(FicheMarquePage)
    # setupUi

    def retranslateUi(self, FicheMarquePage):
        self.etiquette_nom.setText(QCoreApplication.translate("FicheMarquePage", u"&Nom", None))
        self.nom.setPlaceholderText(QCoreApplication.translate("FicheMarquePage", u"Obligatoire, et propre \u00e0 ce marque-page", None))
        self.etiquette_url.setText(QCoreApplication.translate("FicheMarquePage", u"A&dresse", None))
        self.url.setPlaceholderText(QCoreApplication.translate("FicheMarquePage", u"https://\u2026 : l'adresse du flux, obligatoire", None))
        self.tester.setText(QCoreApplication.translate("FicheMarquePage", u"Tester le flux", None))
        self.groupe_streams.setTitle(QCoreApplication.translate("FicheMarquePage", u"Streams qui le suivent", None))
        self.explication_streams.setText(QCoreApplication.translate("FicheMarquePage", u"Ces streams jouent l'adresse du marque-page : une nouvelle adresse vaut pour tous. Un stream choisit son marque-page dans sa fiche.", None))
        self.supprimer.setText(QCoreApplication.translate("FicheMarquePage", u"Supprimer\u2026", None))
#if QT_CONFIG(tooltip)
        self.supprimer.setToolTip(QCoreApplication.translate("FicheMarquePage", u"Supprime l'\u00e9l\u00e9ment de la base, apr\u00e8s confirmation ; aucun fichier n'est touch\u00e9.", None))
#endif // QT_CONFIG(tooltip)
        self.annuler.setText(QCoreApplication.translate("FicheMarquePage", u"Annuler", None))
        self.enregistrer.setText(QCoreApplication.translate("FicheMarquePage", u"Enregistrer", None))
        pass
    # retranslateUi

