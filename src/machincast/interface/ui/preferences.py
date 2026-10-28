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
    QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QSpacerItem, QSpinBox, QTabWidget,
    QVBoxLayout, QWidget)

class Ui_FenetrePreferences(object):
    def setupUi(self, FenetrePreferences):
        if not FenetrePreferences.objectName():
            FenetrePreferences.setObjectName(u"FenetrePreferences")
        self.disposition = QVBoxLayout(FenetrePreferences)
        self.disposition.setObjectName(u"disposition")
        self.pages = QTabWidget(FenetrePreferences)
        self.pages.setObjectName(u"pages")
        self.page_crossfades = QWidget()
        self.page_crossfades.setObjectName(u"page_crossfades")
        self.disposition_crossfades = QVBoxLayout(self.page_crossfades)
        self.disposition_crossfades.setObjectName(u"disposition_crossfades")
        self.groupe_crossfades = QGroupBox(self.page_crossfades)
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


        self.disposition_crossfades.addWidget(self.groupe_crossfades)

        self.groupe_positions = QGroupBox(self.page_crossfades)
        self.groupe_positions.setObjectName(u"groupe_positions")
        self.formulaire_positions = QFormLayout(self.groupe_positions)
        self.formulaire_positions.setObjectName(u"formulaire_positions")
        self.etiquette_position_entree = QLabel(self.groupe_positions)
        self.etiquette_position_entree.setObjectName(u"etiquette_position_entree")

        self.formulaire_positions.setWidget(0, QFormLayout.ItemRole.LabelRole, self.etiquette_position_entree)

        self.position_entree = QComboBox(self.groupe_positions)
        self.position_entree.setObjectName(u"position_entree")

        self.formulaire_positions.setWidget(0, QFormLayout.ItemRole.FieldRole, self.position_entree)

        self.etiquette_position_sortie = QLabel(self.groupe_positions)
        self.etiquette_position_sortie.setObjectName(u"etiquette_position_sortie")

        self.formulaire_positions.setWidget(1, QFormLayout.ItemRole.LabelRole, self.etiquette_position_sortie)

        self.position_sortie = QComboBox(self.groupe_positions)
        self.position_sortie.setObjectName(u"position_sortie")

        self.formulaire_positions.setWidget(1, QFormLayout.ItemRole.FieldRole, self.position_sortie)

        self.place_demonstration = QWidget(self.groupe_positions)
        self.place_demonstration.setObjectName(u"place_demonstration")
        self.place_demonstration.setMinimumSize(QSize(360, 72))

        self.formulaire_positions.setWidget(2, QFormLayout.ItemRole.SpanningRole, self.place_demonstration)

        self.legende_demonstration = QLabel(self.groupe_positions)
        self.legende_demonstration.setObjectName(u"legende_demonstration")
        self.legende_demonstration.setWordWrap(True)

        self.formulaire_positions.setWidget(3, QFormLayout.ItemRole.SpanningRole, self.legende_demonstration)


        self.disposition_crossfades.addWidget(self.groupe_positions)

        self.explication = QLabel(self.page_crossfades)
        self.explication.setObjectName(u"explication")
        self.explication.setWordWrap(True)

        self.disposition_crossfades.addWidget(self.explication)

        self.pages.addTab(self.page_crossfades, "")
        self.page_interface = QWidget()
        self.page_interface.setObjectName(u"page_interface")
        self.disposition_interface = QVBoxLayout(self.page_interface)
        self.disposition_interface.setObjectName(u"disposition_interface")
        self.groupe_accueil = QGroupBox(self.page_interface)
        self.groupe_accueil.setObjectName(u"groupe_accueil")
        self.disposition_accueil = QVBoxLayout(self.groupe_accueil)
        self.disposition_accueil.setObjectName(u"disposition_accueil")
        self.saturation = QCheckBox(self.groupe_accueil)
        self.saturation.setObjectName(u"saturation")

        self.disposition_accueil.addWidget(self.saturation)

        self.suggestions = QCheckBox(self.groupe_accueil)
        self.suggestions.setObjectName(u"suggestions")

        self.disposition_accueil.addWidget(self.suggestions)


        self.disposition_interface.addWidget(self.groupe_accueil)

        self.groupe_icone = QGroupBox(self.page_interface)
        self.groupe_icone.setObjectName(u"groupe_icone")
        self.disposition_icone = QVBoxLayout(self.groupe_icone)
        self.disposition_icone.setObjectName(u"disposition_icone")
        self.ligne_icone = QHBoxLayout()
        self.ligne_icone.setObjectName(u"ligne_icone")
        self.icone_apercu = QLabel(self.groupe_icone)
        self.icone_apercu.setObjectName(u"icone_apercu")
        self.icone_apercu.setMinimumSize(QSize(48, 48))
        self.icone_apercu.setMaximumSize(QSize(48, 48))

        self.ligne_icone.addWidget(self.icone_apercu)

        self.icone_chemin = QLabel(self.groupe_icone)
        self.icone_chemin.setObjectName(u"icone_chemin")
        self.icone_chemin.setWordWrap(True)
        self.icone_chemin.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.ligne_icone.addWidget(self.icone_chemin)

        self.choisir_icone = QPushButton(self.groupe_icone)
        self.choisir_icone.setObjectName(u"choisir_icone")

        self.ligne_icone.addWidget(self.choisir_icone)

        self.icone_par_defaut = QPushButton(self.groupe_icone)
        self.icone_par_defaut.setObjectName(u"icone_par_defaut")

        self.ligne_icone.addWidget(self.icone_par_defaut)

        self.ligne_icone.setStretch(1, 1)

        self.disposition_icone.addLayout(self.ligne_icone)

        self.icone_erreur = QLabel(self.groupe_icone)
        self.icone_erreur.setObjectName(u"icone_erreur")
        self.icone_erreur.setWordWrap(True)

        self.disposition_icone.addWidget(self.icone_erreur)


        self.disposition_interface.addWidget(self.groupe_icone)

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

        self.groupe_silences = QGroupBox(self.page_audio)
        self.groupe_silences.setObjectName(u"groupe_silences")
        self.formulaire_silences = QFormLayout(self.groupe_silences)
        self.formulaire_silences.setObjectName(u"formulaire_silences")
        self.etiquette_seuil_silences = QLabel(self.groupe_silences)
        self.etiquette_seuil_silences.setObjectName(u"etiquette_seuil_silences")

        self.formulaire_silences.setWidget(0, QFormLayout.ItemRole.LabelRole, self.etiquette_seuil_silences)

        self.seuil_silences = QDoubleSpinBox(self.groupe_silences)
        self.seuil_silences.setObjectName(u"seuil_silences")
        self.seuil_silences.setDecimals(1)
        self.seuil_silences.setMinimum(-100.000000000000000)
        self.seuil_silences.setMaximum(-0.100000000000000)
        self.seuil_silences.setSingleStep(1.000000000000000)
        self.seuil_silences.setValue(-40.000000000000000)

        self.formulaire_silences.setWidget(0, QFormLayout.ItemRole.FieldRole, self.seuil_silences)


        self.disposition_audio.addWidget(self.groupe_silences)

        self.explication_silences = QLabel(self.page_audio)
        self.explication_silences.setObjectName(u"explication_silences")
        self.explication_silences.setWordWrap(True)

        self.disposition_audio.addWidget(self.explication_silences)

        self.groupe_blanc_antenne = QGroupBox(self.page_audio)
        self.groupe_blanc_antenne.setObjectName(u"groupe_blanc_antenne")
        self.formulaire_blanc_antenne = QFormLayout(self.groupe_blanc_antenne)
        self.formulaire_blanc_antenne.setObjectName(u"formulaire_blanc_antenne")
        self.secours_blanc = QCheckBox(self.groupe_blanc_antenne)
        self.secours_blanc.setObjectName(u"secours_blanc")

        self.formulaire_blanc_antenne.setWidget(0, QFormLayout.ItemRole.SpanningRole, self.secours_blanc)

        self.etiquette_duree_blanc = QLabel(self.groupe_blanc_antenne)
        self.etiquette_duree_blanc.setObjectName(u"etiquette_duree_blanc")

        self.formulaire_blanc_antenne.setWidget(1, QFormLayout.ItemRole.LabelRole, self.etiquette_duree_blanc)

        self.duree_blanc = QDoubleSpinBox(self.groupe_blanc_antenne)
        self.duree_blanc.setObjectName(u"duree_blanc")
        self.duree_blanc.setDecimals(1)
        self.duree_blanc.setMinimum(1.000000000000000)
        self.duree_blanc.setMaximum(300.000000000000000)
        self.duree_blanc.setSingleStep(1.000000000000000)
        self.duree_blanc.setValue(10.000000000000000)

        self.formulaire_blanc_antenne.setWidget(1, QFormLayout.ItemRole.FieldRole, self.duree_blanc)

        self.etiquette_seuil_blanc = QLabel(self.groupe_blanc_antenne)
        self.etiquette_seuil_blanc.setObjectName(u"etiquette_seuil_blanc")

        self.formulaire_blanc_antenne.setWidget(2, QFormLayout.ItemRole.LabelRole, self.etiquette_seuil_blanc)

        self.seuil_blanc = QDoubleSpinBox(self.groupe_blanc_antenne)
        self.seuil_blanc.setObjectName(u"seuil_blanc")
        self.seuil_blanc.setDecimals(1)
        self.seuil_blanc.setMinimum(-100.000000000000000)
        self.seuil_blanc.setMaximum(-0.100000000000000)
        self.seuil_blanc.setSingleStep(1.000000000000000)
        self.seuil_blanc.setValue(-90.000000000000000)

        self.formulaire_blanc_antenne.setWidget(2, QFormLayout.ItemRole.FieldRole, self.seuil_blanc)


        self.disposition_audio.addWidget(self.groupe_blanc_antenne)

        self.explication_blanc_antenne = QLabel(self.page_audio)
        self.explication_blanc_antenne.setObjectName(u"explication_blanc_antenne")
        self.explication_blanc_antenne.setWordWrap(True)

        self.disposition_audio.addWidget(self.explication_blanc_antenne)

        self.espace_audio = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.disposition_audio.addItem(self.espace_audio)

        self.pages.addTab(self.page_audio, "")
        self.page_base = QWidget()
        self.page_base.setObjectName(u"page_base")
        self.disposition_base = QVBoxLayout(self.page_base)
        self.disposition_base.setObjectName(u"disposition_base")
        self.formulaire_base = QFormLayout()
        self.formulaire_base.setObjectName(u"formulaire_base")
        self.etiquette_peremption = QLabel(self.page_base)
        self.etiquette_peremption.setObjectName(u"etiquette_peremption")

        self.formulaire_base.setWidget(0, QFormLayout.ItemRole.LabelRole, self.etiquette_peremption)

        self.peremption = QSpinBox(self.page_base)
        self.peremption.setObjectName(u"peremption")
        self.peremption.setMinimum(1)
        self.peremption.setMaximum(3650)
        self.peremption.setValue(60)

        self.formulaire_base.setWidget(0, QFormLayout.ItemRole.FieldRole, self.peremption)


        self.disposition_base.addLayout(self.formulaire_base)

        self.explication_peremption = QLabel(self.page_base)
        self.explication_peremption.setObjectName(u"explication_peremption")
        self.explication_peremption.setWordWrap(True)

        self.disposition_base.addWidget(self.explication_peremption)

        self.espace_base = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.disposition_base.addItem(self.espace_base)

        self.pages.addTab(self.page_base, "")

        self.disposition.addWidget(self.pages)

        self.boutons = QDialogButtonBox(FenetrePreferences)
        self.boutons.setObjectName(u"boutons")
        self.boutons.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.disposition.addWidget(self.boutons)

#if QT_CONFIG(shortcut)
        self.etiquette_granularite.setBuddy(self.granularite)
        self.etiquette_maximum.setBuddy(self.maximum)
        self.etiquette_position_entree.setBuddy(self.position_entree)
        self.etiquette_position_sortie.setBuddy(self.position_sortie)
        self.etiquette_antenne.setBuddy(self.antenne)
        self.etiquette_preecoute.setBuddy(self.preecoute)
        self.etiquette_seuil_silences.setBuddy(self.seuil_silences)
        self.etiquette_duree_blanc.setBuddy(self.duree_blanc)
        self.etiquette_seuil_blanc.setBuddy(self.seuil_blanc)
        self.etiquette_peremption.setBuddy(self.peremption)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(FenetrePreferences)

        QMetaObject.connectSlotsByName(FenetrePreferences)
    # setupUi

    def retranslateUi(self, FenetrePreferences):
        FenetrePreferences.setWindowTitle(QCoreApplication.translate("FenetrePreferences", u"Pr\u00e9f\u00e9rences", None))
        self.groupe_crossfades.setTitle(QCoreApplication.translate("FenetrePreferences", u"Dur\u00e9es", None))
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
        self.groupe_positions.setTitle(QCoreApplication.translate("FenetrePreferences", u"Position des fondus, pour un sonore jou\u00e9 sans ses silences", None))
#if QT_CONFIG(tooltip)
        self.groupe_positions.setToolTip(QCoreApplication.translate("FenetrePreferences", u"O\u00f9 tombent les fondus par rapport au d\u00e9but et \u00e0 la fin d\u00e9tect\u00e9s d'un sonore jou\u00e9 sans ses silences, quelle que soit sa banque", None))
#endif // QT_CONFIG(tooltip)
        self.etiquette_position_entree.setText(QCoreApplication.translate("FenetrePreferences", u"Le fade-in, au d\u00e9but d\u00e9tect\u00e9", None))
        self.etiquette_position_sortie.setText(QCoreApplication.translate("FenetrePreferences", u"Le fade-out, \u00e0 la fin d\u00e9tect\u00e9e", None))
#if QT_CONFIG(tooltip)
        self.place_demonstration.setToolTip(QCoreApplication.translate("FenetrePreferences", u"D\u00e9monstration : un sonore de 30 s, aux silences de 3 s au d\u00e9but et 4 s \u00e0 la fin, retir\u00e9s \u00e0 l'antenne, avec les crossfades par d\u00e9faut saisis", None))
#endif // QT_CONFIG(tooltip)
        self.legende_demonstration.setText("")
        self.explication.setText(QCoreApplication.translate("FenetrePreferences", u"Les fiches ouvertes ensuite suivent ces r\u00e9glages. Machin lecture prend les dur\u00e9es par d\u00e9faut \u00e0 son prochain d\u00e9marrage.", None))
        self.pages.setTabText(self.pages.indexOf(self.page_crossfades), QCoreApplication.translate("FenetrePreferences", u"Crossfades", None))
        self.groupe_accueil.setTitle(QCoreApplication.translate("FenetrePreferences", u"Accueil", None))
        self.saturation.setText(QCoreApplication.translate("FenetrePreferences", u"Afficher le voyant de saturation de l'accueil", None))
#if QT_CONFIG(tooltip)
        self.saturation.setToolTip(QCoreApplication.translate("FenetrePreferences", u"Le voyant \u00ab Saturation \u00bb de la colonne Antenne, au-dessus du VU-m\u00e8tre ; le VU-m\u00e8tre montre toujours les cr\u00eates.", None))
#endif // QT_CONFIG(tooltip)
        self.suggestions.setText(QCoreApplication.translate("FenetrePreferences", u"Proposer au lancement ce qui manque pour d\u00e9marrer", None))
#if QT_CONFIG(tooltip)
        self.suggestions.setToolTip(QCoreApplication.translate("FenetrePreferences", u"Fil musical, banques de base et p\u00e9riph\u00e9rique de l'antenne, dans une fen\u00eatre au lancement de l'interface.", None))
#endif // QT_CONFIG(tooltip)
        self.groupe_icone.setTitle(QCoreApplication.translate("FenetrePreferences", u"Ic\u00f4ne de l'application", None))
#if QT_CONFIG(tooltip)
        self.groupe_icone.setToolTip(QCoreApplication.translate("FenetrePreferences", u"L'ic\u00f4ne des fen\u00eatres de MachinCast, de son raccourci dans le menu des applications et sur le bureau, et de la barre des t\u00e2ches.", None))
#endif // QT_CONFIG(tooltip)
        self.choisir_icone.setText(QCoreApplication.translate("FenetrePreferences", u"&Choisir une image\u2026", None))
#if QT_CONFIG(tooltip)
        self.choisir_icone.setToolTip(QCoreApplication.translate("FenetrePreferences", u"Une image SVG, PNG ou JPEG, de pr\u00e9f\u00e9rence carr\u00e9e", None))
#endif // QT_CONFIG(tooltip)
        self.icone_par_defaut.setText(QCoreApplication.translate("FenetrePreferences", u"Ic\u00f4ne de MachinCast", None))
#if QT_CONFIG(tooltip)
        self.icone_par_defaut.setToolTip(QCoreApplication.translate("FenetrePreferences", u"Revenir \u00e0 l'ic\u00f4ne de MachinCast", None))
#endif // QT_CONFIG(tooltip)
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
        self.groupe_silences.setTitle(QCoreApplication.translate("FenetrePreferences", u"D\u00e9tection de silence", None))
        self.etiquette_seuil_silences.setText(QCoreApplication.translate("FenetrePreferences", u"&Seuil de silence", None))
#if QT_CONFIG(tooltip)
        self.seuil_silences.setToolTip(QCoreApplication.translate("FenetrePreferences", u"Niveau cr\u00eate sous lequel le d\u00e9but et la fin d'un sonore sont un silence ; 0 dB est la pleine \u00e9chelle", None))
#endif // QT_CONFIG(tooltip)
        self.seuil_silences.setSuffix(QCoreApplication.translate("FenetrePreferences", u" dB", None))
        self.explication_silences.setText(QCoreApplication.translate("FenetrePreferences", u"L'audit complet mesure les silences au d\u00e9but et \u00e0 la fin de chaque fichier \u00e0 ce seuil ; un nouveau seuil vaut pour les audits suivants. Une banque, ou un sonore, choisit d'\u00eatre jou\u00e9 sans ses silences.", None))
        self.groupe_blanc_antenne.setTitle(QCoreApplication.translate("FenetrePreferences", u"Blanc dans un sonore, \u00e0 l'antenne", None))
#if QT_CONFIG(tooltip)
        self.secours_blanc.setToolTip(QCoreApplication.translate("FenetrePreferences", u"Coch\u00e9, un blanc fait passer au sonore suivant, ou au secours d'un stream ; sinon, il est seulement not\u00e9 dans le log", None))
#endif // QT_CONFIG(tooltip)
        self.secours_blanc.setText(QCoreApplication.translate("FenetrePreferences", u"Passer au sonore suivant, ou au secours d'un s&tream", None))
        self.etiquette_duree_blanc.setText(QCoreApplication.translate("FenetrePreferences", u"D&ur\u00e9e d'un blanc", None))
#if QT_CONFIG(tooltip)
        self.duree_blanc.setToolTip(QCoreApplication.translate("FenetrePreferences", u"Dur\u00e9e pendant laquelle un sonore qui joue doit rester sous le niveau d'un blanc", None))
#endif // QT_CONFIG(tooltip)
        self.duree_blanc.setSuffix(QCoreApplication.translate("FenetrePreferences", u" s", None))
        self.etiquette_seuil_blanc.setText(QCoreApplication.translate("FenetrePreferences", u"&Niveau d'un blanc", None))
#if QT_CONFIG(tooltip)
        self.seuil_blanc.setToolTip(QCoreApplication.translate("FenetrePreferences", u"Niveau cr\u00eate sous lequel un sonore qui joue ne donne plus de son ; 0 dB est la pleine \u00e9chelle", None))
#endif // QT_CONFIG(tooltip)
        self.seuil_blanc.setSuffix(QCoreApplication.translate("FenetrePreferences", u" dB", None))
        self.explication_blanc_antenne.setText(QCoreApplication.translate("FenetrePreferences", u"Un sonore qui reste cette dur\u00e9e sous ce niveau, pendant qu'il joue, est not\u00e9 dans le log. Coch\u00e9, un fichier laisse aussit\u00f4t l'antenne au sonore suivant, et un stream \u00e0 son secours, jusqu'au retour de son son. Ce n'est pas un silence, au d\u00e9but ou \u00e0 la fin d'un fichier. Machin lecture prend ces r\u00e9glages \u00e0 son prochain d\u00e9marrage.", None))
        self.pages.setTabText(self.pages.indexOf(self.page_audio), QCoreApplication.translate("FenetrePreferences", u"Audio", None))
        self.etiquette_peremption.setText(QCoreApplication.translate("FenetrePreferences", u"&Dur\u00e9e de p\u00e9remption", None))
        self.peremption.setSuffix(QCoreApplication.translate("FenetrePreferences", u" jours", None))
        self.explication_peremption.setText(QCoreApplication.translate("FenetrePreferences", u"Machin purge efface de la base les passages de l'airplay et les lignes du log plus vieux que cette dur\u00e9e, et les sonores, banques, s\u00e9quences et \u00e9v\u00e9nements supprim\u00e9s depuis plus longtemps. Il ne touche jamais aux fichiers sonores.", None))
        self.pages.setTabText(self.pages.indexOf(self.page_base), QCoreApplication.translate("FenetrePreferences", u"Base", None))
    # retranslateUi

