# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'liste.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QTableView, QVBoxLayout, QWidget)

class Ui_Liste(object):
    def setupUi(self, Liste):
        if not Liste.objectName():
            Liste.setObjectName(u"Liste")
        Liste.resize(1100, 700)
        self.disposition = QVBoxLayout(Liste)
        self.disposition.setObjectName(u"disposition")
        self.bandeau = QHBoxLayout()
        self.bandeau.setObjectName(u"bandeau")
        self.filtre = QLineEdit(Liste)
        self.filtre.setObjectName(u"filtre")
        self.filtre.setClearButtonEnabled(True)

        self.bandeau.addWidget(self.filtre)

        self.compte = QLabel(Liste)
        self.compte.setObjectName(u"compte")

        self.bandeau.addWidget(self.compte)

        self.ajouter_fichiers = QPushButton(Liste)
        self.ajouter_fichiers.setObjectName(u"ajouter_fichiers")
        self.ajouter_fichiers.setVisible(False)

        self.bandeau.addWidget(self.ajouter_fichiers)

        self.nouveau = QPushButton(Liste)
        self.nouveau.setObjectName(u"nouveau")
        self.nouveau.setVisible(False)

        self.bandeau.addWidget(self.nouveau)


        self.disposition.addLayout(self.bandeau)

        self.table = QTableView(Liste)
        self.table.setObjectName(u"table")
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)

        self.disposition.addWidget(self.table)


        self.retranslateUi(Liste)

        QMetaObject.connectSlotsByName(Liste)
    # setupUi

    def retranslateUi(self, Liste):
        self.filtre.setPlaceholderText(QCoreApplication.translate("Liste", u"Filtrer\u2026", None))
        self.compte.setText(QCoreApplication.translate("Liste", u"\u2014", None))
#if QT_CONFIG(tooltip)
        self.ajouter_fichiers.setToolTip(QCoreApplication.translate("Liste", u"Les fichiers sont r\u00e9f\u00e9renc\u00e9s l\u00e0 o\u00f9 ils sont, sans copie, et v\u00e9rifi\u00e9s aussit\u00f4t ; on peut aussi les d\u00e9poser sur la liste.", None))
#endif // QT_CONFIG(tooltip)
        pass
    # retranslateUi

