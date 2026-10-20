# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'preecoute.ui'
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
    QLabel, QSizePolicy, QSlider, QToolButton,
    QVBoxLayout, QWidget)

class Ui_FenetrePreecoute(object):
    def setupUi(self, FenetrePreecoute):
        if not FenetrePreecoute.objectName():
            FenetrePreecoute.setObjectName(u"FenetrePreecoute")
        FenetrePreecoute.resize(520, 360)
        self.disposition = QVBoxLayout(FenetrePreecoute)
        self.disposition.setObjectName(u"disposition")
        self.source = QLabel(FenetrePreecoute)
        self.source.setObjectName(u"source")
        self.source.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.source.setWordWrap(True)

        self.disposition.addWidget(self.source)

        self.lecteur = QHBoxLayout()
        self.lecteur.setObjectName(u"lecteur")
        self.lecture = QToolButton(FenetrePreecoute)
        self.lecture.setObjectName(u"lecture")

        self.lecteur.addWidget(self.lecture)

        self.arret = QToolButton(FenetrePreecoute)
        self.arret.setObjectName(u"arret")

        self.lecteur.addWidget(self.arret)

        self.position = QSlider(FenetrePreecoute)
        self.position.setObjectName(u"position")
        self.position.setMaximum(1000)
        self.position.setOrientation(Qt.Orientation.Horizontal)

        self.lecteur.addWidget(self.position)

        self.temps = QLabel(FenetrePreecoute)
        self.temps.setObjectName(u"temps")

        self.lecteur.addWidget(self.temps)

        self.lecteur.setStretch(2, 1)

        self.disposition.addLayout(self.lecteur)

        self.place_vumetre = QWidget(FenetrePreecoute)
        self.place_vumetre.setObjectName(u"place_vumetre")
        self.place_vumetre.setMinimumSize(QSize(0, 36))

        self.disposition.addWidget(self.place_vumetre)

        self.informations = QFormLayout()
        self.informations.setObjectName(u"informations")
        self.intitule_etat = QLabel(FenetrePreecoute)
        self.intitule_etat.setObjectName(u"intitule_etat")

        self.informations.setWidget(0, QFormLayout.ItemRole.LabelRole, self.intitule_etat)

        self.etat = QLabel(FenetrePreecoute)
        self.etat.setObjectName(u"etat")

        self.informations.setWidget(0, QFormLayout.ItemRole.FieldRole, self.etat)

        self.intitule_format = QLabel(FenetrePreecoute)
        self.intitule_format.setObjectName(u"intitule_format")

        self.informations.setWidget(1, QFormLayout.ItemRole.LabelRole, self.intitule_format)

        self.format = QLabel(FenetrePreecoute)
        self.format.setObjectName(u"format")

        self.informations.setWidget(1, QFormLayout.ItemRole.FieldRole, self.format)

        self.intitule_debit = QLabel(FenetrePreecoute)
        self.intitule_debit.setObjectName(u"intitule_debit")

        self.informations.setWidget(2, QFormLayout.ItemRole.LabelRole, self.intitule_debit)

        self.debit = QLabel(FenetrePreecoute)
        self.debit.setObjectName(u"debit")

        self.informations.setWidget(2, QFormLayout.ItemRole.FieldRole, self.debit)

        self.intitule_echantillonnage = QLabel(FenetrePreecoute)
        self.intitule_echantillonnage.setObjectName(u"intitule_echantillonnage")

        self.informations.setWidget(3, QFormLayout.ItemRole.LabelRole, self.intitule_echantillonnage)

        self.echantillonnage = QLabel(FenetrePreecoute)
        self.echantillonnage.setObjectName(u"echantillonnage")

        self.informations.setWidget(3, QFormLayout.ItemRole.FieldRole, self.echantillonnage)

        self.intitule_canaux = QLabel(FenetrePreecoute)
        self.intitule_canaux.setObjectName(u"intitule_canaux")

        self.informations.setWidget(4, QFormLayout.ItemRole.LabelRole, self.intitule_canaux)

        self.canaux = QLabel(FenetrePreecoute)
        self.canaux.setObjectName(u"canaux")

        self.informations.setWidget(4, QFormLayout.ItemRole.FieldRole, self.canaux)

        self.intitule_predecode = QLabel(FenetrePreecoute)
        self.intitule_predecode.setObjectName(u"intitule_predecode")

        self.informations.setWidget(5, QFormLayout.ItemRole.LabelRole, self.intitule_predecode)

        self.predecode = QLabel(FenetrePreecoute)
        self.predecode.setObjectName(u"predecode")

        self.informations.setWidget(5, QFormLayout.ItemRole.FieldRole, self.predecode)

        self.intitule_sortie = QLabel(FenetrePreecoute)
        self.intitule_sortie.setObjectName(u"intitule_sortie")

        self.informations.setWidget(6, QFormLayout.ItemRole.LabelRole, self.intitule_sortie)

        self.sortie = QComboBox(FenetrePreecoute)
        self.sortie.setObjectName(u"sortie")

        self.informations.setWidget(6, QFormLayout.ItemRole.FieldRole, self.sortie)


        self.disposition.addLayout(self.informations)

        self.message = QLabel(FenetrePreecoute)
        self.message.setObjectName(u"message")
        self.message.setWordWrap(True)

        self.disposition.addWidget(self.message)

#if QT_CONFIG(shortcut)
        self.intitule_sortie.setBuddy(self.sortie)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(FenetrePreecoute)

        QMetaObject.connectSlotsByName(FenetrePreecoute)
    # setupUi

    def retranslateUi(self, FenetrePreecoute):
        FenetrePreecoute.setWindowTitle(QCoreApplication.translate("FenetrePreecoute", u"Pr\u00e9-\u00e9coute", None))
        self.source.setText(QCoreApplication.translate("FenetrePreecoute", u"\u2014", None))
#if QT_CONFIG(tooltip)
        self.lecture.setToolTip(QCoreApplication.translate("FenetrePreecoute", u"Lecture", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(accessibility)
        self.lecture.setAccessibleName(QCoreApplication.translate("FenetrePreecoute", u"Lecture", None))
#endif // QT_CONFIG(accessibility)
        self.lecture.setText(QCoreApplication.translate("FenetrePreecoute", u"\u23f5", None))
#if QT_CONFIG(tooltip)
        self.arret.setToolTip(QCoreApplication.translate("FenetrePreecoute", u"Arr\u00eat", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(accessibility)
        self.arret.setAccessibleName(QCoreApplication.translate("FenetrePreecoute", u"Arr\u00eat", None))
#endif // QT_CONFIG(accessibility)
        self.arret.setText(QCoreApplication.translate("FenetrePreecoute", u"\u23f9", None))
#if QT_CONFIG(tooltip)
        self.position.setToolTip(QCoreApplication.translate("FenetrePreecoute", u"Position dans le fichier", None))
#endif // QT_CONFIG(tooltip)
        self.temps.setText(QCoreApplication.translate("FenetrePreecoute", u"\u2014", None))
        self.intitule_etat.setText(QCoreApplication.translate("FenetrePreecoute", u"\u00c9tat", None))
        self.etat.setText(QCoreApplication.translate("FenetrePreecoute", u"\u2014", None))
        self.intitule_format.setText(QCoreApplication.translate("FenetrePreecoute", u"Format", None))
        self.format.setText(QCoreApplication.translate("FenetrePreecoute", u"\u2014", None))
        self.intitule_debit.setText(QCoreApplication.translate("FenetrePreecoute", u"D\u00e9bit", None))
        self.debit.setText(QCoreApplication.translate("FenetrePreecoute", u"\u2014", None))
        self.intitule_echantillonnage.setText(QCoreApplication.translate("FenetrePreecoute", u"\u00c9chantillonnage", None))
        self.echantillonnage.setText(QCoreApplication.translate("FenetrePreecoute", u"\u2014", None))
        self.intitule_canaux.setText(QCoreApplication.translate("FenetrePreecoute", u"Canaux", None))
        self.canaux.setText(QCoreApplication.translate("FenetrePreecoute", u"\u2014", None))
        self.intitule_predecode.setText(QCoreApplication.translate("FenetrePreecoute", u"Pr\u00e9-d\u00e9cod\u00e9", None))
#if QT_CONFIG(tooltip)
        self.predecode.setToolTip(QCoreApplication.translate("FenetrePreecoute", u"Son re\u00e7u et d\u00e9cod\u00e9 d'avance, pr\u00eat \u00e0 \u00eatre jou\u00e9", None))
#endif // QT_CONFIG(tooltip)
        self.predecode.setText(QCoreApplication.translate("FenetrePreecoute", u"\u2014", None))
        self.intitule_sortie.setText(QCoreApplication.translate("FenetrePreecoute", u"Sortie", None))
#if QT_CONFIG(tooltip)
        self.sortie.setToolTip(QCoreApplication.translate("FenetrePreecoute", u"P\u00e9riph\u00e9rique de pr\u00e9-\u00e9coute, jamais celui de l'antenne", None))
#endif // QT_CONFIG(tooltip)
        self.message.setText("")
    # retranslateUi

