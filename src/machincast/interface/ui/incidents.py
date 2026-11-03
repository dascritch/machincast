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

class Ui_IncidentScreen(object):
    def setupUi(self, IncidentScreen):
        if not IncidentScreen.objectName():
            IncidentScreen.setObjectName(u"IncidentScreen")
        IncidentScreen.resize(1000, 600)
        self.arrangement = QVBoxLayout(IncidentScreen)
        self.arrangement.setObjectName(u"arrangement")
        self.banner = QHBoxLayout()
        self.banner.setObjectName(u"banner")
        self.filter_ = QLineEdit(IncidentScreen)
        self.filter_.setObjectName(u"filter_")
        self.filter_.setClearButtonEnabled(True)

        self.banner.addWidget(self.filter_)

        self.information = QCheckBox(IncidentScreen)
        self.information.setObjectName(u"information")

        self.banner.addWidget(self.information)

        self.count = QLabel(IncidentScreen)
        self.count.setObjectName(u"count")

        self.banner.addWidget(self.count)


        self.arrangement.addLayout(self.banner)

        self.table = QTableView(IncidentScreen)
        self.table.setObjectName(u"table")
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)

        self.arrangement.addWidget(self.table)


        self.retranslateUi(IncidentScreen)

        QMetaObject.connectSlotsByName(IncidentScreen)
    # setupUi

    def retranslateUi(self, IncidentScreen):
        self.filter_.setPlaceholderText(QCoreApplication.translate("IncidentScreen", u"Filter\u2026", None))
        self.information.setText(QCoreApplication.translate("IncidentScreen", u"Also show the information entries", None))
#if QT_CONFIG(tooltip)
        self.table.setToolTip(QCoreApplication.translate("IncidentScreen", u"A double-click on the sound, the bank or the event of an entry opens its card.", None))
#endif // QT_CONFIG(tooltip)
        pass
    # retranslateUi

