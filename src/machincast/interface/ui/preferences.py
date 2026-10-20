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
    QGroupBox, QLabel, QSizePolicy, QTabWidget,
    QVBoxLayout, QWidget)

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

        self.disposition.addWidget(self.pages)

        self.boutons = QDialogButtonBox(FenetrePreferences)
        self.boutons.setObjectName(u"boutons")
        self.boutons.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.disposition.addWidget(self.boutons)

#if QT_CONFIG(shortcut)
        self.etiquette_granularite.setBuddy(self.granularite)
        self.etiquette_maximum.setBuddy(self.maximum)
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
    # retranslateUi

