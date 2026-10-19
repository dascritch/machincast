# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'incidents.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QSizePolicy,
    QTableView, QVBoxLayout, QWidget)

class Ui_EcranIncidents(object):
    def setupUi(self, EcranIncidents):
        if not EcranIncidents.objectName():
            EcranIncidents.setObjectName(u"EcranIncidents")
        EcranIncidents.resize(1000, 600)
        self.disposition = QVBoxLayout(EcranIncidents)
        self.disposition.setObjectName(u"disposition")
        self.bandeau = QHBoxLayout()
        self.bandeau.setObjectName(u"bandeau")
        self.filtre = QLineEdit(EcranIncidents)
        self.filtre.setObjectName(u"filtre")
        self.filtre.setClearButtonEnabled(True)

        self.bandeau.addWidget(self.filtre)

        self.informations = QCheckBox(EcranIncidents)
        self.informations.setObjectName(u"informations")

        self.bandeau.addWidget(self.informations)

        self.compte = QLabel(EcranIncidents)
        self.compte.setObjectName(u"compte")

        self.bandeau.addWidget(self.compte)


        self.disposition.addLayout(self.bandeau)

        self.table = QTableView(EcranIncidents)
        self.table.setObjectName(u"table")
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)

        self.disposition.addWidget(self.table)


        self.retranslateUi(EcranIncidents)

        QMetaObject.connectSlotsByName(EcranIncidents)
    # setupUi

    def retranslateUi(self, EcranIncidents):
        self.filtre.setPlaceholderText(QCoreApplication.translate("EcranIncidents", u"Filtrer\u2026", None))
        self.informations.setText(QCoreApplication.translate("EcranIncidents", u"Montrer aussi les informations", None))
#if QT_CONFIG(tooltip)
        self.table.setToolTip(QCoreApplication.translate("EcranIncidents", u"Un double-clic sur le sonore, la banque ou l'\u00e9v\u00e9nement d'une entr\u00e9e ouvre sa fiche.", None))
#endif // QT_CONFIG(tooltip)
        pass
    # retranslateUi

