# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'preferences.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QLabel, QSizePolicy, QSpacerItem,
    QTabWidget, QVBoxLayout, QWidget)

class Ui_FenetrePreferences(object):
    def setupUi(self, FenetrePreferences):
        if not FenetrePreferences.objectName():
            FenetrePreferences.setObjectName(u"FenetrePreferences")
        self.disposition = QVBoxLayout(FenetrePreferences)
        self.disposition.setObjectName(u"disposition")
        self.pages = QTabWidget(FenetrePreferences)
        self.pages.setObjectName(u"pages")
        self.page_interface = QWidget()
        self.page_interface.setObjectName(u"page_interface")
        self.disposition_interface = QVBoxLayout(self.page_interface)
        self.disposition_interface.setObjectName(u"disposition_interface")
        self.groupe_crossfades = QGroupBox(self.page_interface)
        self.groupe_crossfades.setObjectName(u"groupe_crossfades")
        self.formulaire_crossfades = QFormLayout(self.groupe_crossfades)
        self.formulaire_crossfades.setObjectName(u"formulaire_crossfades")
        self.etiquette_granularite = QLabel(self.groupe_crossfades)
        self.etiquette_granularite.setObjectName(u"etiquette_granularite")

        self.formulaire_crossfades.setWidget(0, QFormLayout.ItemRole.LabelRole, self.etiquette_granularite)

        self.granularite = QComboBox(self.groupe_crossfades)
        self.granularite.setObjectName(u"granularite")

        self.formulaire_crossfades.setWidget(0, QFormLayout.ItemRole.FieldRole, self.granularite)

        self.etiquette_maximum = QLabel(self.groupe_crossfades)
        self.etiquette_maximum.setObjectName(u"etiquette_maximum")

        self.formulaire_crossfades.setWidget(1, QFormLayout.ItemRole.LabelRole, self.etiquette_maximum)

        self.maximum = QDoubleSpinBox(self.groupe_crossfades)
        self.maximum.setObjectName(u"maximum")
        self.maximum.setMaximum(600.000000000000000)

        self.formulaire_crossfades.setWidget(1, QFormLayout.ItemRole.FieldRole, self.maximum)

        self.a_debut = QCheckBox(self.groupe_crossfades)
        self.a_debut.setObjectName(u"a_debut")

        self.formulaire_crossfades.setWidget(2, QFormLayout.ItemRole.LabelRole, self.a_debut)

        self.debut = QDoubleSpinBox(self.groupe_crossfades)
        self.debut.setObjectName(u"debut")
        self.debut.setEnabled(False)

        self.formulaire_crossfades.setWidget(2, QFormLayout.ItemRole.FieldRole, self.debut)

        self.a_fin = QCheckBox(self.groupe_crossfades)
        self.a_fin.setObjectName(u"a_fin")

        self.formulaire_crossfades.setWidget(3, QFormLayout.ItemRole.LabelRole, self.a_fin)

        self.fin = QDoubleSpinBox(self.groupe_crossfades)
        self.fin.setObjectName(u"fin")
        self.fin.setEnabled(False)

        self.formulaire_crossfades.setWidget(3, QFormLayout.ItemRole.FieldRole, self.fin)


        self.disposition_interface.addWidget(self.groupe_crossfades)

        self.explication = QLabel(self.page_interface)
        self.explication.setObjectName(u"explication")
        self.explication.setWordWrap(True)

        self.disposition_interface.addWidget(self.explication)

        self.pages.addTab(self.page_interface, "")
        self.page_audio = QWidget()
        self.page_audio.setObjectName(u"page_audio")
        self.disposition_audio = QVBoxLayout(self.page_audio)
        self.disposition_audio.setObjectName(u"disposition_audio")
        self.groupe_peripheriques = QGroupBox(self.page_audio)
        self.groupe_peripheriques.setObjectName(u"groupe_peripheriques")
        self.formulaire_peripheriques = QFormLayout(self.groupe_peripheriques)
        self.formulaire_peripheriques.setObjectName(u"formulaire_peripheriques")
        self.etiquette_antenne = QLabel(self.groupe_peripheriques)
        self.etiquette_antenne.setObjectName(u"etiquette_antenne")

        self.formulaire_peripheriques.setWidget(0, QFormLayout.ItemRole.LabelRole, self.etiquette_antenne)

        self.antenne = QComboBox(self.groupe_peripheriques)
        self.antenne.setObjectName(u"antenne")

        self.formulaire_peripheriques.setWidget(0, QFormLayout.ItemRole.FieldRole, self.antenne)

        self.etiquette_preecoute = QLabel(self.groupe_peripheriques)
        self.etiquette_preecoute.setObjectName(u"etiquette_preecoute")

        self.formulaire_peripheriques.setWidget(1, QFormLayout.ItemRole.LabelRole, self.etiquette_preecoute)

        self.preecoute = QComboBox(self.groupe_peripheriques)
        self.preecoute.setObjectName(u"preecoute")

        self.formulaire_peripheriques.setWidget(1, QFormLayout.ItemRole.FieldRole, self.preecoute)


        self.disposition_audio.addWidget(self.groupe_peripheriques)

        self.explication_audio = QLabel(self.page_audio)
        self.explication_audio.setObjectName(u"explication_audio")
        self.explication_audio.setWordWrap(True)

        self.disposition_audio.addWidget(self.explication_audio)

        self.groupe_blancs = QGroupBox(self.page_audio)
        self.groupe_blancs.setObjectName(u"groupe_blancs")
        self.formulaire_blancs = QFormLayout(self.groupe_blancs)
        self.formulaire_blancs.setObjectName(u"formulaire_blancs")
        self.etiquette_seuil_blancs = QLabel(self.groupe_blancs)
        self.etiquette_seuil_blancs.setObjectName(u"etiquette_seuil_blancs")

        self.formulaire_blancs.setWidget(0, QFormLayout.ItemRole.LabelRole, self.etiquette_seuil_blancs)

        self.seuil_blancs = QDoubleSpinBox(self.groupe_blancs)
        self.seuil_blancs.setObjectName(u"seuil_blancs")
        self.seuil_blancs.setDecimals(1)
        self.seuil_blancs.setMinimum(-100.000000000000000)
        self.seuil_blancs.setMaximum(-0.100000000000000)
        self.seuil_blancs.setSingleStep(1.000000000000000)
        self.seuil_blancs.setValue(-40.000000000000000)

        self.formulaire_blancs.setWidget(0, QFormLayout.ItemRole.FieldRole, self.seuil_blancs)


        self.disposition_audio.addWidget(self.groupe_blancs)

        self.explication_blancs = QLabel(self.page_audio)
        self.explication_blancs.setObjectName(u"explication_blancs")
        self.explication_blancs.setWordWrap(True)

        self.disposition_audio.addWidget(self.explication_blancs)

        self.espace_audio = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.disposition_audio.addItem(self.espace_audio)

        self.pages.addTab(self.page_audio, "")

        self.disposition.addWidget(self.pages)

        self.boutons = QDialogButtonBox(FenetrePreferences)
        self.boutons.setObjectName(u"boutons")
        self.boutons.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.disposition.addWidget(self.boutons)

#if QT_CONFIG(shortcut)
        self.etiquette_granularite.setBuddy(self.granularite)
        self.etiquette_maximum.setBuddy(self.maximum)
        self.etiquette_antenne.setBuddy(self.antenne)
        self.etiquette_preecoute.setBuddy(self.preecoute)
        self.etiquette_seuil_blancs.setBuddy(self.seuil_blancs)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(FenetrePreferences)

        QMetaObject.connectSlotsByName(FenetrePreferences)
    # setupUi

    def retranslateUi(self, FenetrePreferences):
        FenetrePreferences.setWindowTitle(QCoreApplication.translate("FenetrePreferences", u"Pr\u00e9f\u00e9rences", None))
        self.groupe_crossfades.setTitle(QCoreApplication.translate("FenetrePreferences", u"Crossfades", None))
        self.etiquette_granularite.setText(QCoreApplication.translate("FenetrePreferences", u"&Granularit\u00e9", None))
#if QT_CONFIG(tooltip)
        self.granularite.setToolTip(QCoreApplication.translate("FenetrePreferences", u"Le pas de tous les crossfades de l'interface", None))
#endif // QT_CONFIG(tooltip)
        self.etiquette_maximum.setText(QCoreApplication.translate("FenetrePreferences", u"Dur\u00e9e &maximale", None))
#if QT_CONFIG(tooltip)
        self.maximum.setToolTip(QCoreApplication.translate("FenetrePreferences", u"Le crossfade le plus long que proposent les fiches", None))
#endif // QT_CONFIG(tooltip)
        self.maximum.setSuffix(QCoreApplication.translate("FenetrePreferences", u" s", None))
        self.a_debut.setText(QCoreApplication.translate("FenetrePreferences", u"&D\u00e9but par d\u00e9faut", None))
#if QT_CONFIG(tooltip)
        self.a_debut.setToolTip(QCoreApplication.translate("FenetrePreferences", u"Le crossfade de d\u00e9but d'un sonore qui n'en a pas de param\u00e9tr\u00e9, et que sa banque ne r\u00e8gle pas", None))
#endif // QT_CONFIG(tooltip)
        self.debut.setSuffix(QCoreApplication.translate("FenetrePreferences", u" s", None))
        self.a_fin.setText(QCoreApplication.translate("FenetrePreferences", u"&Fin par d\u00e9faut", None))
#if QT_CONFIG(tooltip)
        self.a_fin.setToolTip(QCoreApplication.translate("FenetrePreferences", u"Le crossfade de fin d'un sonore qui n'en a pas de param\u00e9tr\u00e9, et que sa banque ne r\u00e8gle pas", None))
#endif // QT_CONFIG(tooltip)
        self.fin.setSuffix(QCoreApplication.translate("FenetrePreferences", u" s", None))
        self.explication.setText(QCoreApplication.translate("FenetrePreferences", u"Les fiches ouvertes ensuite suivent ces r\u00e9glages. Machin lecture prend les dur\u00e9es par d\u00e9faut \u00e0 son prochain d\u00e9marrage.", None))
        self.pages.setTabText(self.pages.indexOf(self.page_interface), QCoreApplication.translate("FenetrePreferences", u"Interface", None))
        self.groupe_peripheriques.setTitle(QCoreApplication.translate("FenetrePreferences", u"P\u00e9riph\u00e9riques", None))
        self.etiquette_antenne.setText(QCoreApplication.translate("FenetrePreferences", u"&Antenne", None))
#if QT_CONFIG(tooltip)
        self.antenne.setToolTip(QCoreApplication.translate("FenetrePreferences", u"Le p\u00e9riph\u00e9rique sur lequel Machin lecture diffuse l'antenne", None))
#endif // QT_CONFIG(tooltip)
        self.etiquette_preecoute.setText(QCoreApplication.translate("FenetrePreferences", u"&Pr\u00e9-\u00e9coute", None))
#if QT_CONFIG(tooltip)
        self.preecoute.setToolTip(QCoreApplication.translate("FenetrePreferences", u"Le p\u00e9riph\u00e9rique de la pr\u00e9-\u00e9coute de l'interface, jamais celui de l'antenne", None))
#endif // QT_CONFIG(tooltip)
        self.explication_audio.setText(QCoreApplication.translate("FenetrePreferences", u"Machin lecture prend le p\u00e9riph\u00e9rique de l'antenne \u00e0 son prochain d\u00e9marrage ; sans lui, il refuse de diffuser. La pr\u00e9-\u00e9coute ne peut jamais utiliser le p\u00e9riph\u00e9rique de l'antenne : chacun est gris\u00e9 dans l'autre choix.", None))
        self.groupe_blancs.setTitle(QCoreApplication.translate("FenetrePreferences", u"D\u00e9tection de blanc", None))
        self.etiquette_seuil_blancs.setText(QCoreApplication.translate("FenetrePreferences", u"&Seuil de blanc", None))
#if QT_CONFIG(tooltip)
        self.seuil_blancs.setToolTip(QCoreApplication.translate("FenetrePreferences", u"Niveau cr\u00eate sous lequel le d\u00e9but et la fin d'un sonore sont un blanc ; 0 dB est la pleine \u00e9chelle", None))
#endif // QT_CONFIG(tooltip)
        self.seuil_blancs.setSuffix(QCoreApplication.translate("FenetrePreferences", u" dB", None))
        self.explication_blancs.setText(QCoreApplication.translate("FenetrePreferences", u"L'audit complet mesure les blancs au d\u00e9but et \u00e0 la fin de chaque fichier \u00e0 ce seuil ; un nouveau seuil vaut pour les audits suivants. Une banque, ou un sonore, choisit d'\u00eatre jou\u00e9 sans ses blancs.", None))
        self.pages.setTabText(self.pages.indexOf(self.page_audio), QCoreApplication.translate("FenetrePreferences", u"Audio", None))
    # retranslateUi

