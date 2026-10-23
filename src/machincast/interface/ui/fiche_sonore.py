# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'fiche_sonore.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QDateTimeEdit, QDoubleSpinBox, QFormLayout, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QRadioButton, QScrollArea,
    QSizePolicy, QSpacerItem, QSpinBox, QTableWidget,
    QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

from machincast.interface.curseur import CurseurDeDuree

class Ui_FicheSonore(object):
    def setupUi(self, FicheSonore):
        if not FicheSonore.objectName():
            FicheSonore.setObjectName(u"FicheSonore")
        FicheSonore.resize(1100, 760)
        self.disposition = QVBoxLayout(FicheSonore)
        self.disposition.setObjectName(u"disposition")
        self.place_frise = QWidget(FicheSonore)
        self.place_frise.setObjectName(u"place_frise")

        self.disposition.addWidget(self.place_frise)

        self.corps = QHBoxLayout()
        self.corps.setObjectName(u"corps")
        self.defilement = QScrollArea(FicheSonore)
        self.defilement.setObjectName(u"defilement")
        self.defilement.setWidgetResizable(True)
        self.contenu = QWidget()
        self.contenu.setObjectName(u"contenu")
        self.disposition_contenu = QVBoxLayout(self.contenu)
        self.disposition_contenu.setObjectName(u"disposition_contenu")
        self.groupe_sonore = QGroupBox(self.contenu)
        self.groupe_sonore.setObjectName(u"groupe_sonore")
        self.formulaire_sonore = QFormLayout(self.groupe_sonore)
        self.formulaire_sonore.setObjectName(u"formulaire_sonore")
        self.etiquette_type = QLabel(self.groupe_sonore)
        self.etiquette_type.setObjectName(u"etiquette_type")

        self.formulaire_sonore.setWidget(0, QFormLayout.ItemRole.LabelRole, self.etiquette_type)

        self.type_sonore = QLabel(self.groupe_sonore)
        self.type_sonore.setObjectName(u"type_sonore")

        self.formulaire_sonore.setWidget(0, QFormLayout.ItemRole.FieldRole, self.type_sonore)

        self.etiquette_emplacement = QLabel(self.groupe_sonore)
        self.etiquette_emplacement.setObjectName(u"etiquette_emplacement")

        self.formulaire_sonore.setWidget(1, QFormLayout.ItemRole.LabelRole, self.etiquette_emplacement)

        self.ligne_emplacement = QHBoxLayout()
        self.ligne_emplacement.setObjectName(u"ligne_emplacement")
        self.emplacement = QLineEdit(self.groupe_sonore)
        self.emplacement.setObjectName(u"emplacement")
        self.emplacement.setReadOnly(True)

        self.ligne_emplacement.addWidget(self.emplacement)

        self.ouvrir_dossier = QToolButton(self.groupe_sonore)
        self.ouvrir_dossier.setObjectName(u"ouvrir_dossier")
        icon = QIcon(QIcon.fromTheme(u"folder-open"))
        self.ouvrir_dossier.setIcon(icon)

        self.ligne_emplacement.addWidget(self.ouvrir_dossier)


        self.formulaire_sonore.setLayout(1, QFormLayout.ItemRole.FieldRole, self.ligne_emplacement)

        self.etiquette_duree = QLabel(self.groupe_sonore)
        self.etiquette_duree.setObjectName(u"etiquette_duree")

        self.formulaire_sonore.setWidget(2, QFormLayout.ItemRole.LabelRole, self.etiquette_duree)

        self.duree = QLabel(self.groupe_sonore)
        self.duree.setObjectName(u"duree")

        self.formulaire_sonore.setWidget(2, QFormLayout.ItemRole.FieldRole, self.duree)

        self.etiquette_etat = QLabel(self.groupe_sonore)
        self.etiquette_etat.setObjectName(u"etiquette_etat")

        self.formulaire_sonore.setWidget(3, QFormLayout.ItemRole.LabelRole, self.etiquette_etat)

        self.etat = QComboBox(self.groupe_sonore)
        self.etat.setObjectName(u"etat")

        self.formulaire_sonore.setWidget(3, QFormLayout.ItemRole.FieldRole, self.etat)


        self.disposition_contenu.addWidget(self.groupe_sonore)

        self.groupe_stream = QGroupBox(self.contenu)
        self.groupe_stream.setObjectName(u"groupe_stream")
        self.grille_stream = QGridLayout(self.groupe_stream)
        self.grille_stream.setObjectName(u"grille_stream")
        self.par_adresse = QRadioButton(self.groupe_stream)
        self.par_adresse.setObjectName(u"par_adresse")

        self.grille_stream.addWidget(self.par_adresse, 0, 0, 1, 1)

        self.url_stream = QLineEdit(self.groupe_stream)
        self.url_stream.setObjectName(u"url_stream")

        self.grille_stream.addWidget(self.url_stream, 0, 1, 1, 1)

        self.par_feed = QRadioButton(self.groupe_stream)
        self.par_feed.setObjectName(u"par_feed")

        self.grille_stream.addWidget(self.par_feed, 1, 0, 1, 1)

        self.feed = QComboBox(self.groupe_stream)
        self.feed.setObjectName(u"feed")

        self.grille_stream.addWidget(self.feed, 1, 1, 1, 1)

        self.etiquette_secours = QLabel(self.groupe_stream)
        self.etiquette_secours.setObjectName(u"etiquette_secours")

        self.grille_stream.addWidget(self.etiquette_secours, 2, 0, 1, 1)

        self.secours = QComboBox(self.groupe_stream)
        self.secours.setObjectName(u"secours")

        self.grille_stream.addWidget(self.secours, 2, 1, 1, 1)

        self.tester = QPushButton(self.groupe_stream)
        self.tester.setObjectName(u"tester")

        self.grille_stream.addWidget(self.tester, 3, 0, 1, 1)

        self.resultat_essai = QLabel(self.groupe_stream)
        self.resultat_essai.setObjectName(u"resultat_essai")
        self.resultat_essai.setWordWrap(True)

        self.grille_stream.addWidget(self.resultat_essai, 3, 1, 1, 1)


        self.disposition_contenu.addWidget(self.groupe_stream)

        self.groupe_metadonnees = QGroupBox(self.contenu)
        self.groupe_metadonnees.setObjectName(u"groupe_metadonnees")
        self.formulaire_metadonnees = QFormLayout(self.groupe_metadonnees)
        self.formulaire_metadonnees.setObjectName(u"formulaire_metadonnees")
        self.etiquette_artiste = QLabel(self.groupe_metadonnees)
        self.etiquette_artiste.setObjectName(u"etiquette_artiste")

        self.formulaire_metadonnees.setWidget(0, QFormLayout.ItemRole.LabelRole, self.etiquette_artiste)

        self.artiste = QLineEdit(self.groupe_metadonnees)
        self.artiste.setObjectName(u"artiste")
        self.artiste.setMaxLength(255)

        self.formulaire_metadonnees.setWidget(0, QFormLayout.ItemRole.FieldRole, self.artiste)

        self.etiquette_titre = QLabel(self.groupe_metadonnees)
        self.etiquette_titre.setObjectName(u"etiquette_titre")

        self.formulaire_metadonnees.setWidget(1, QFormLayout.ItemRole.LabelRole, self.etiquette_titre)

        self.titre = QLineEdit(self.groupe_metadonnees)
        self.titre.setObjectName(u"titre")
        self.titre.setMaxLength(255)

        self.formulaire_metadonnees.setWidget(1, QFormLayout.ItemRole.FieldRole, self.titre)

        self.etiquette_annee = QLabel(self.groupe_metadonnees)
        self.etiquette_annee.setObjectName(u"etiquette_annee")

        self.formulaire_metadonnees.setWidget(2, QFormLayout.ItemRole.LabelRole, self.etiquette_annee)

        self.annee = QLineEdit(self.groupe_metadonnees)
        self.annee.setObjectName(u"annee")
        self.annee.setMaxLength(4)

        self.formulaire_metadonnees.setWidget(2, QFormLayout.ItemRole.FieldRole, self.annee)

        self.etiquette_album = QLabel(self.groupe_metadonnees)
        self.etiquette_album.setObjectName(u"etiquette_album")

        self.formulaire_metadonnees.setWidget(3, QFormLayout.ItemRole.LabelRole, self.etiquette_album)

        self.album = QLineEdit(self.groupe_metadonnees)
        self.album.setObjectName(u"album")
        self.album.setMaxLength(255)

        self.formulaire_metadonnees.setWidget(3, QFormLayout.ItemRole.FieldRole, self.album)

        self.etiquette_artiste_album = QLabel(self.groupe_metadonnees)
        self.etiquette_artiste_album.setObjectName(u"etiquette_artiste_album")

        self.formulaire_metadonnees.setWidget(4, QFormLayout.ItemRole.LabelRole, self.etiquette_artiste_album)

        self.artiste_album = QLineEdit(self.groupe_metadonnees)
        self.artiste_album.setObjectName(u"artiste_album")
        self.artiste_album.setMaxLength(255)

        self.formulaire_metadonnees.setWidget(4, QFormLayout.ItemRole.FieldRole, self.artiste_album)

        self.etiquette_genre = QLabel(self.groupe_metadonnees)
        self.etiquette_genre.setObjectName(u"etiquette_genre")

        self.formulaire_metadonnees.setWidget(5, QFormLayout.ItemRole.LabelRole, self.etiquette_genre)

        self.genre = QLineEdit(self.groupe_metadonnees)
        self.genre.setObjectName(u"genre")
        self.genre.setMaxLength(255)

        self.formulaire_metadonnees.setWidget(5, QFormLayout.ItemRole.FieldRole, self.genre)

        self.etiquette_compositeur = QLabel(self.groupe_metadonnees)
        self.etiquette_compositeur.setObjectName(u"etiquette_compositeur")

        self.formulaire_metadonnees.setWidget(6, QFormLayout.ItemRole.LabelRole, self.etiquette_compositeur)

        self.compositeur = QLineEdit(self.groupe_metadonnees)
        self.compositeur.setObjectName(u"compositeur")
        self.compositeur.setMaxLength(255)

        self.formulaire_metadonnees.setWidget(6, QFormLayout.ItemRole.FieldRole, self.compositeur)

        self.etiquette_label = QLabel(self.groupe_metadonnees)
        self.etiquette_label.setObjectName(u"etiquette_label")

        self.formulaire_metadonnees.setWidget(7, QFormLayout.ItemRole.LabelRole, self.etiquette_label)

        self.label = QLineEdit(self.groupe_metadonnees)
        self.label.setObjectName(u"label")
        self.label.setMaxLength(255)

        self.formulaire_metadonnees.setWidget(7, QFormLayout.ItemRole.FieldRole, self.label)

        self.etiquette_piste = QLabel(self.groupe_metadonnees)
        self.etiquette_piste.setObjectName(u"etiquette_piste")

        self.formulaire_metadonnees.setWidget(8, QFormLayout.ItemRole.LabelRole, self.etiquette_piste)

        self.piste = QLineEdit(self.groupe_metadonnees)
        self.piste.setObjectName(u"piste")
        self.piste.setMaxLength(4)

        self.formulaire_metadonnees.setWidget(8, QFormLayout.ItemRole.FieldRole, self.piste)

        self.etiquette_autres = QLabel(self.groupe_metadonnees)
        self.etiquette_autres.setObjectName(u"etiquette_autres")

        self.formulaire_metadonnees.setWidget(9, QFormLayout.ItemRole.LabelRole, self.etiquette_autres)

        self.autres_metadonnees = QLabel(self.groupe_metadonnees)
        self.autres_metadonnees.setObjectName(u"autres_metadonnees")
        self.autres_metadonnees.setWordWrap(True)

        self.formulaire_metadonnees.setWidget(9, QFormLayout.ItemRole.FieldRole, self.autres_metadonnees)


        self.disposition_contenu.addWidget(self.groupe_metadonnees)

        self.groupe_diffusion = QGroupBox(self.contenu)
        self.groupe_diffusion.setObjectName(u"groupe_diffusion")
        self.formulaire_diffusion = QFormLayout(self.groupe_diffusion)
        self.formulaire_diffusion.setObjectName(u"formulaire_diffusion")
        self.etiquette_masquage = QLabel(self.groupe_diffusion)
        self.etiquette_masquage.setObjectName(u"etiquette_masquage")

        self.formulaire_diffusion.setWidget(0, QFormLayout.ItemRole.LabelRole, self.etiquette_masquage)

        self.masquage = QComboBox(self.groupe_diffusion)
        self.masquage.setObjectName(u"masquage")

        self.formulaire_diffusion.setWidget(0, QFormLayout.ItemRole.FieldRole, self.masquage)

        self.a_debut = QCheckBox(self.groupe_diffusion)
        self.a_debut.setObjectName(u"a_debut")

        self.formulaire_diffusion.setWidget(1, QFormLayout.ItemRole.LabelRole, self.a_debut)

        self.debut_diffusion = QDateTimeEdit(self.groupe_diffusion)
        self.debut_diffusion.setObjectName(u"debut_diffusion")
        self.debut_diffusion.setCalendarPopup(True)
        self.debut_diffusion.setEnabled(False)

        self.formulaire_diffusion.setWidget(1, QFormLayout.ItemRole.FieldRole, self.debut_diffusion)

        self.a_fin = QCheckBox(self.groupe_diffusion)
        self.a_fin.setObjectName(u"a_fin")

        self.formulaire_diffusion.setWidget(2, QFormLayout.ItemRole.LabelRole, self.a_fin)

        self.fin_diffusion = QDateTimeEdit(self.groupe_diffusion)
        self.fin_diffusion.setObjectName(u"fin_diffusion")
        self.fin_diffusion.setCalendarPopup(True)
        self.fin_diffusion.setEnabled(False)

        self.formulaire_diffusion.setWidget(2, QFormLayout.ItemRole.FieldRole, self.fin_diffusion)

        self.etiquette_max_lectures = QLabel(self.groupe_diffusion)
        self.etiquette_max_lectures.setObjectName(u"etiquette_max_lectures")

        self.formulaire_diffusion.setWidget(3, QFormLayout.ItemRole.LabelRole, self.etiquette_max_lectures)

        self.max_lectures = QSpinBox(self.groupe_diffusion)
        self.max_lectures.setObjectName(u"max_lectures")
        self.max_lectures.setMaximum(1000000)

        self.formulaire_diffusion.setWidget(3, QFormLayout.ItemRole.FieldRole, self.max_lectures)


        self.disposition_contenu.addWidget(self.groupe_diffusion)

        self.groupe_blancs = QGroupBox(self.contenu)
        self.groupe_blancs.setObjectName(u"groupe_blancs")
        self.formulaire_blancs = QFormLayout(self.groupe_blancs)
        self.formulaire_blancs.setObjectName(u"formulaire_blancs")
        self.detection_blancs = QCheckBox(self.groupe_blancs)
        self.detection_blancs.setObjectName(u"detection_blancs")

        self.formulaire_blancs.setWidget(0, QFormLayout.ItemRole.SpanningRole, self.detection_blancs)

        self.a_debut_detecte = QCheckBox(self.groupe_blancs)
        self.a_debut_detecte.setObjectName(u"a_debut_detecte")

        self.formulaire_blancs.setWidget(1, QFormLayout.ItemRole.LabelRole, self.a_debut_detecte)

        self.debut_detecte = QDoubleSpinBox(self.groupe_blancs)
        self.debut_detecte.setObjectName(u"debut_detecte")
        self.debut_detecte.setEnabled(False)
        self.debut_detecte.setDecimals(2)
        self.debut_detecte.setMaximum(86400.000000000000000)
        self.debut_detecte.setSingleStep(0.010000000000000)

        self.formulaire_blancs.setWidget(1, QFormLayout.ItemRole.FieldRole, self.debut_detecte)

        self.a_fin_detectee = QCheckBox(self.groupe_blancs)
        self.a_fin_detectee.setObjectName(u"a_fin_detectee")

        self.formulaire_blancs.setWidget(2, QFormLayout.ItemRole.LabelRole, self.a_fin_detectee)

        self.fin_detectee = QDoubleSpinBox(self.groupe_blancs)
        self.fin_detectee.setObjectName(u"fin_detectee")
        self.fin_detectee.setEnabled(False)
        self.fin_detectee.setDecimals(2)
        self.fin_detectee.setMaximum(86400.000000000000000)
        self.fin_detectee.setSingleStep(0.010000000000000)

        self.formulaire_blancs.setWidget(2, QFormLayout.ItemRole.FieldRole, self.fin_detectee)

        self.a_crossfade_debut = QCheckBox(self.groupe_blancs)
        self.a_crossfade_debut.setObjectName(u"a_crossfade_debut")

        self.formulaire_blancs.setWidget(3, QFormLayout.ItemRole.LabelRole, self.a_crossfade_debut)

        self.crossfade_debut = CurseurDeDuree(self.groupe_blancs)
        self.crossfade_debut.setObjectName(u"crossfade_debut")
        self.crossfade_debut.setEnabled(False)

        self.formulaire_blancs.setWidget(3, QFormLayout.ItemRole.FieldRole, self.crossfade_debut)

        self.a_crossfade_fin = QCheckBox(self.groupe_blancs)
        self.a_crossfade_fin.setObjectName(u"a_crossfade_fin")

        self.formulaire_blancs.setWidget(4, QFormLayout.ItemRole.LabelRole, self.a_crossfade_fin)

        self.crossfade_fin = CurseurDeDuree(self.groupe_blancs)
        self.crossfade_fin.setObjectName(u"crossfade_fin")
        self.crossfade_fin.setEnabled(False)

        self.formulaire_blancs.setWidget(4, QFormLayout.ItemRole.FieldRole, self.crossfade_fin)


        self.disposition_contenu.addWidget(self.groupe_blancs)

        self.groupe_relations = QGroupBox(self.contenu)
        self.groupe_relations.setObjectName(u"groupe_relations")
        self.disposition_relations = QVBoxLayout(self.groupe_relations)
        self.disposition_relations.setObjectName(u"disposition_relations")
        self.relations = QTableWidget(self.groupe_relations)
        if (self.relations.columnCount() < 2):
            self.relations.setColumnCount(2)
        __qtablewidgetitem = QTableWidgetItem()
        self.relations.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.relations.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        self.relations.setObjectName(u"relations")
        self.relations.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.relations.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.relations.horizontalHeader().setStretchLastSection(True)
        self.relations.verticalHeader().setVisible(False)

        self.disposition_relations.addWidget(self.relations)

        self.aucune_relation = QLabel(self.groupe_relations)
        self.aucune_relation.setObjectName(u"aucune_relation")

        self.disposition_relations.addWidget(self.aucune_relation)


        self.disposition_contenu.addWidget(self.groupe_relations)

        self.groupe_fichier = QGroupBox(self.contenu)
        self.groupe_fichier.setObjectName(u"groupe_fichier")
        self.formulaire_fichier = QFormLayout(self.groupe_fichier)
        self.formulaire_fichier.setObjectName(u"formulaire_fichier")
        self.etiquette_type_mime = QLabel(self.groupe_fichier)
        self.etiquette_type_mime.setObjectName(u"etiquette_type_mime")

        self.formulaire_fichier.setWidget(0, QFormLayout.ItemRole.LabelRole, self.etiquette_type_mime)

        self.type_mime = QLabel(self.groupe_fichier)
        self.type_mime.setObjectName(u"type_mime")
        self.type_mime.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.formulaire_fichier.setWidget(0, QFormLayout.ItemRole.FieldRole, self.type_mime)

        self.etiquette_encodage = QLabel(self.groupe_fichier)
        self.etiquette_encodage.setObjectName(u"etiquette_encodage")

        self.formulaire_fichier.setWidget(1, QFormLayout.ItemRole.LabelRole, self.etiquette_encodage)

        self.encodage = QLabel(self.groupe_fichier)
        self.encodage.setObjectName(u"encodage")
        self.encodage.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.formulaire_fichier.setWidget(1, QFormLayout.ItemRole.FieldRole, self.encodage)

        self.etiquette_taille = QLabel(self.groupe_fichier)
        self.etiquette_taille.setObjectName(u"etiquette_taille")

        self.formulaire_fichier.setWidget(2, QFormLayout.ItemRole.LabelRole, self.etiquette_taille)

        self.taille = QLabel(self.groupe_fichier)
        self.taille.setObjectName(u"taille")
        self.taille.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.formulaire_fichier.setWidget(2, QFormLayout.ItemRole.FieldRole, self.taille)

        self.etiquette_cree_le = QLabel(self.groupe_fichier)
        self.etiquette_cree_le.setObjectName(u"etiquette_cree_le")

        self.formulaire_fichier.setWidget(3, QFormLayout.ItemRole.LabelRole, self.etiquette_cree_le)

        self.cree_le = QLabel(self.groupe_fichier)
        self.cree_le.setObjectName(u"cree_le")
        self.cree_le.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.formulaire_fichier.setWidget(3, QFormLayout.ItemRole.FieldRole, self.cree_le)

        self.etiquette_modifie_le = QLabel(self.groupe_fichier)
        self.etiquette_modifie_le.setObjectName(u"etiquette_modifie_le")

        self.formulaire_fichier.setWidget(4, QFormLayout.ItemRole.LabelRole, self.etiquette_modifie_le)

        self.modifie_le = QLabel(self.groupe_fichier)
        self.modifie_le.setObjectName(u"modifie_le")
        self.modifie_le.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.formulaire_fichier.setWidget(4, QFormLayout.ItemRole.FieldRole, self.modifie_le)

        self.etiquette_verifie_le = QLabel(self.groupe_fichier)
        self.etiquette_verifie_le.setObjectName(u"etiquette_verifie_le")

        self.formulaire_fichier.setWidget(5, QFormLayout.ItemRole.LabelRole, self.etiquette_verifie_le)

        self.verifie_le = QLabel(self.groupe_fichier)
        self.verifie_le.setObjectName(u"verifie_le")
        self.verifie_le.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.formulaire_fichier.setWidget(5, QFormLayout.ItemRole.FieldRole, self.verifie_le)


        self.disposition_contenu.addWidget(self.groupe_fichier)

        self.champs_edites = QLabel(self.contenu)
        self.champs_edites.setObjectName(u"champs_edites")
        self.champs_edites.setWordWrap(True)

        self.disposition_contenu.addWidget(self.champs_edites)

        self.espace_contenu = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.disposition_contenu.addItem(self.espace_contenu)

        self.defilement.setWidget(self.contenu)

        self.corps.addWidget(self.defilement)

        self.groupe_passages = QGroupBox(FicheSonore)
        self.groupe_passages.setObjectName(u"groupe_passages")
        self.disposition_passages = QVBoxLayout(self.groupe_passages)
        self.disposition_passages.setObjectName(u"disposition_passages")
        self.passages = QTableWidget(self.groupe_passages)
        if (self.passages.columnCount() < 7):
            self.passages.setColumnCount(7)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.passages.setHorizontalHeaderItem(0, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.passages.setHorizontalHeaderItem(1, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.passages.setHorizontalHeaderItem(2, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.passages.setHorizontalHeaderItem(3, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.passages.setHorizontalHeaderItem(4, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.passages.setHorizontalHeaderItem(5, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.passages.setHorizontalHeaderItem(6, __qtablewidgetitem8)
        self.passages.setObjectName(u"passages")
        self.passages.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.passages.setAlternatingRowColors(True)
        self.passages.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.passages.horizontalHeader().setStretchLastSection(True)
        self.passages.verticalHeader().setVisible(False)

        self.disposition_passages.addWidget(self.passages)


        self.corps.addWidget(self.groupe_passages)

        self.corps.setStretch(0, 1)
        self.corps.setStretch(1, 1)

        self.disposition.addLayout(self.corps)

        self.pied = QHBoxLayout()
        self.pied.setObjectName(u"pied")
        self.supprimer = QPushButton(FicheSonore)
        self.supprimer.setObjectName(u"supprimer")

        self.pied.addWidget(self.supprimer)

        self.preecouter = QPushButton(FicheSonore)
        self.preecouter.setObjectName(u"preecouter")

        self.pied.addWidget(self.preecouter)

        self.verifier = QPushButton(FicheSonore)
        self.verifier.setObjectName(u"verifier")

        self.pied.addWidget(self.verifier)

        self.message = QLabel(FicheSonore)
        self.message.setObjectName(u"message")
        self.message.setWordWrap(True)

        self.pied.addWidget(self.message)

        self.annuler = QPushButton(FicheSonore)
        self.annuler.setObjectName(u"annuler")

        self.pied.addWidget(self.annuler)

        self.enregistrer = QPushButton(FicheSonore)
        self.enregistrer.setObjectName(u"enregistrer")

        self.pied.addWidget(self.enregistrer)

        self.pied.setStretch(3, 1)

        self.disposition.addLayout(self.pied)

        self.disposition.setStretch(1, 1)
#if QT_CONFIG(shortcut)
        self.etiquette_etat.setBuddy(self.etat)
        self.etiquette_secours.setBuddy(self.secours)
        self.etiquette_artiste.setBuddy(self.artiste)
        self.etiquette_titre.setBuddy(self.titre)
        self.etiquette_annee.setBuddy(self.annee)
        self.etiquette_album.setBuddy(self.album)
        self.etiquette_artiste_album.setBuddy(self.artiste_album)
        self.etiquette_genre.setBuddy(self.genre)
        self.etiquette_compositeur.setBuddy(self.compositeur)
        self.etiquette_label.setBuddy(self.label)
        self.etiquette_piste.setBuddy(self.piste)
        self.etiquette_masquage.setBuddy(self.masquage)
        self.etiquette_max_lectures.setBuddy(self.max_lectures)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(FicheSonore)

        self.enregistrer.setDefault(True)


        QMetaObject.connectSlotsByName(FicheSonore)
    # setupUi

    def retranslateUi(self, FicheSonore):
#if QT_CONFIG(tooltip)
        self.place_frise.setToolTip(QCoreApplication.translate("FicheSonore", u"Le fichier tel que l'antenne le jouera, selon les r\u00e9glages de la fiche, m\u00eame pas encore enregistr\u00e9s", None))
#endif // QT_CONFIG(tooltip)
        self.groupe_sonore.setTitle(QCoreApplication.translate("FicheSonore", u"Sonore", None))
        self.etiquette_type.setText(QCoreApplication.translate("FicheSonore", u"Type", None))
        self.etiquette_emplacement.setText(QCoreApplication.translate("FicheSonore", u"Emplacement", None))
#if QT_CONFIG(tooltip)
        self.ouvrir_dossier.setToolTip(QCoreApplication.translate("FicheSonore", u"Ouvrir le dossier du fichier dans le navigateur de fichiers", None))
#endif // QT_CONFIG(tooltip)
        self.ouvrir_dossier.setText(QCoreApplication.translate("FicheSonore", u"Dossier\u2026", None))
        self.etiquette_duree.setText(QCoreApplication.translate("FicheSonore", u"Dur\u00e9e", None))
        self.etiquette_etat.setText(QCoreApplication.translate("FicheSonore", u"\u00c9&tat", None))
        self.groupe_stream.setTitle(QCoreApplication.translate("FicheSonore", u"Stream", None))
        self.par_adresse.setText(QCoreApplication.translate("FicheSonore", u"Adresse &directe", None))
        self.par_feed.setText(QCoreApplication.translate("FicheSonore", u"&Feed", None))
        self.etiquette_secours.setText(QCoreApplication.translate("FicheSonore", u"\u00c9v\u00e9nement de &secours", None))
        self.tester.setText(QCoreApplication.translate("FicheSonore", u"&Tester le flux", None))
        self.groupe_metadonnees.setTitle(QCoreApplication.translate("FicheSonore", u"M\u00e9tadonn\u00e9es", None))
        self.etiquette_artiste.setText(QCoreApplication.translate("FicheSonore", u"&Artiste", None))
        self.etiquette_titre.setText(QCoreApplication.translate("FicheSonore", u"Tit&re", None))
        self.etiquette_annee.setText(QCoreApplication.translate("FicheSonore", u"Ann\u00e9e", None))
        self.etiquette_album.setText(QCoreApplication.translate("FicheSonore", u"Album", None))
        self.etiquette_artiste_album.setText(QCoreApplication.translate("FicheSonore", u"Artiste de l'album", None))
        self.etiquette_genre.setText(QCoreApplication.translate("FicheSonore", u"Genre", None))
        self.etiquette_compositeur.setText(QCoreApplication.translate("FicheSonore", u"Compositeur", None))
        self.etiquette_label.setText(QCoreApplication.translate("FicheSonore", u"Label", None))
        self.etiquette_piste.setText(QCoreApplication.translate("FicheSonore", u"Piste", None))
        self.etiquette_autres.setText(QCoreApplication.translate("FicheSonore", u"Autres", None))
        self.groupe_diffusion.setTitle(QCoreApplication.translate("FicheSonore", u"Diffusion", None))
        self.etiquette_masquage.setText(QCoreApplication.translate("FicheSonore", u"Artiste et titre", None))
        self.a_debut.setText(QCoreApplication.translate("FicheSonore", u"Diffusion \u00e0 partir du", None))
        self.debut_diffusion.setDisplayFormat(QCoreApplication.translate("FicheSonore", u"dd/MM/yyyy HH:mm", None))
        self.a_fin.setText(QCoreApplication.translate("FicheSonore", u"Diffusion jusqu'au", None))
        self.fin_diffusion.setDisplayFormat(QCoreApplication.translate("FicheSonore", u"dd/MM/yyyy HH:mm", None))
        self.etiquette_max_lectures.setText(QCoreApplication.translate("FicheSonore", u"Maximum de lectures", None))
        self.max_lectures.setSpecialValueText(QCoreApplication.translate("FicheSonore", u"illimit\u00e9", None))
        self.groupe_blancs.setTitle(QCoreApplication.translate("FicheSonore", u"Enchainement", None))
        self.detection_blancs.setText(QCoreApplication.translate("FicheSonore", u"Jouer sans les blancs d\u00e9tect\u00e9s", None))
#if QT_CONFIG(tooltip)
        self.detection_blancs.setToolTip(QCoreApplication.translate("FicheSonore", u"Coch\u00e9, le sonore est jou\u00e9 de son d\u00e9but d\u00e9tect\u00e9 \u00e0 sa fin d\u00e9tect\u00e9e, m\u00eame hors d'une banque qui retire les blancs.", None))
#endif // QT_CONFIG(tooltip)
        self.a_debut_detecte.setText(QCoreApplication.translate("FicheSonore", u"D\u00e9but d\u00e9tect\u00e9", None))
#if QT_CONFIG(tooltip)
        self.a_debut_detecte.setToolTip(QCoreApplication.translate("FicheSonore", u"Blanc au d\u00e9but du fichier, mesur\u00e9 par l'audit complet. D\u00e9coch\u00e9, aucun blanc n'est d\u00e9tect\u00e9 : le d\u00e9but n'est pas rogn\u00e9.", None))
#endif // QT_CONFIG(tooltip)
        self.debut_detecte.setSuffix(QCoreApplication.translate("FicheSonore", u" s", None))
        self.a_fin_detectee.setText(QCoreApplication.translate("FicheSonore", u"Fin d\u00e9tect\u00e9e", None))
#if QT_CONFIG(tooltip)
        self.a_fin_detectee.setToolTip(QCoreApplication.translate("FicheSonore", u"Blanc \u00e0 la fin du fichier, compt\u00e9 depuis sa fin, mesur\u00e9 par l'audit complet. D\u00e9coch\u00e9, aucun blanc n'est d\u00e9tect\u00e9 : la fin n'est pas rogn\u00e9e.", None))
#endif // QT_CONFIG(tooltip)
        self.fin_detectee.setSuffix(QCoreApplication.translate("FicheSonore", u" s", None))
        self.a_crossfade_debut.setText(QCoreApplication.translate("FicheSonore", u"Crossfade de d\u00e9but", None))
#if QT_CONFIG(tooltip)
        self.a_crossfade_debut.setToolTip(QCoreApplication.translate("FicheSonore", u"D\u00e9coch\u00e9, le crossfade n'est pas param\u00e9tr\u00e9 : il vient de la banque, ou des pr\u00e9f\u00e9rences. 0 seconde en est un.", None))
#endif // QT_CONFIG(tooltip)
        self.a_crossfade_fin.setText(QCoreApplication.translate("FicheSonore", u"Crossfade de fin", None))
#if QT_CONFIG(tooltip)
        self.a_crossfade_fin.setToolTip(QCoreApplication.translate("FicheSonore", u"D\u00e9coch\u00e9, le crossfade n'est pas param\u00e9tr\u00e9 : il vient de la banque, ou des pr\u00e9f\u00e9rences. 0 seconde en est un.", None))
#endif // QT_CONFIG(tooltip)
        self.groupe_relations.setTitle(QCoreApplication.translate("FicheSonore", u"Relations", None))
        ___qtablewidgetitem = self.relations.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("FicheSonore", u"Genre", None))
        ___qtablewidgetitem1 = self.relations.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("FicheSonore", u"Nom", None))
#if QT_CONFIG(tooltip)
        self.relations.setToolTip(QCoreApplication.translate("FicheSonore", u"Double-clic : ouvrir la fiche", None))
#endif // QT_CONFIG(tooltip)
        self.aucune_relation.setText(QCoreApplication.translate("FicheSonore", u"Aucune s\u00e9quence, banque ni \u00e9v\u00e9nement ne cite ce sonore.", None))
        self.groupe_fichier.setTitle(QCoreApplication.translate("FicheSonore", u"Fichier", None))
        self.etiquette_type_mime.setText(QCoreApplication.translate("FicheSonore", u"Type", None))
        self.etiquette_encodage.setText(QCoreApplication.translate("FicheSonore", u"Encodage moyen", None))
        self.etiquette_taille.setText(QCoreApplication.translate("FicheSonore", u"Taille", None))
        self.etiquette_cree_le.setText(QCoreApplication.translate("FicheSonore", u"Cr\u00e9\u00e9 le", None))
        self.etiquette_modifie_le.setText(QCoreApplication.translate("FicheSonore", u"Modifi\u00e9 le", None))
        self.etiquette_verifie_le.setText(QCoreApplication.translate("FicheSonore", u"Derni\u00e8re v\u00e9rification compl\u00e8te", None))
        self.groupe_passages.setTitle(QCoreApplication.translate("FicheSonore", u"Derniers passages", None))
        ___qtablewidgetitem2 = self.passages.horizontalHeaderItem(0)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("FicheSonore", u"D\u00e9but", None))
        ___qtablewidgetitem3 = self.passages.horizontalHeaderItem(1)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("FicheSonore", u"Fin", None))
        ___qtablewidgetitem4 = self.passages.horizontalHeaderItem(2)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("FicheSonore", u"Dur\u00e9e", None))
        ___qtablewidgetitem5 = self.passages.horizontalHeaderItem(3)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("FicheSonore", u"\u00c9v\u00e9nement", None))
        ___qtablewidgetitem6 = self.passages.horizontalHeaderItem(4)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("FicheSonore", u"S\u00e9quence", None))
        ___qtablewidgetitem7 = self.passages.horizontalHeaderItem(5)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("FicheSonore", u"Banque", None))
        ___qtablewidgetitem8 = self.passages.horizontalHeaderItem(6)
        ___qtablewidgetitem8.setText(QCoreApplication.translate("FicheSonore", u"Incidents", None))
        self.supprimer.setText(QCoreApplication.translate("FicheSonore", u"Supprimer\u2026", None))
#if QT_CONFIG(tooltip)
        self.supprimer.setToolTip(QCoreApplication.translate("FicheSonore", u"Supprime l'\u00e9l\u00e9ment de la base, apr\u00e8s confirmation ; aucun fichier n'est touch\u00e9.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.preecouter.setToolTip(QCoreApplication.translate("FicheSonore", u"\u00c9couter le sonore sur la sortie de pr\u00e9-\u00e9coute, jamais sur l'antenne", None))
#endif // QT_CONFIG(tooltip)
        self.preecouter.setText(QCoreApplication.translate("FicheSonore", u"Pr\u00e9-\u00e9coute\u2026", None))
#if QT_CONFIG(tooltip)
        self.verifier.setToolTip(QCoreApplication.translate("FicheSonore", u"D\u00e9coder le fichier en entier et mesurer ses blancs, comme l'audit complet de Machin indexation, pour ce seul sonore", None))
#endif // QT_CONFIG(tooltip)
        self.verifier.setText(QCoreApplication.translate("FicheSonore", u"V\u00e9rification compl\u00e8te", None))
        self.annuler.setText(QCoreApplication.translate("FicheSonore", u"Annuler", None))
        self.enregistrer.setText(QCoreApplication.translate("FicheSonore", u"Enregistrer", None))
        pass
    # retranslateUi

