# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'list_view.ui'
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

class Ui_List(object):
    def setupUi(self, List):
        if not List.objectName():
            List.setObjectName(u"List")
        List.resize(1100, 700)
        self.arrangement = QVBoxLayout(List)
        self.arrangement.setObjectName(u"arrangement")
        self.banner = QHBoxLayout()
        self.banner.setObjectName(u"banner")
        self.filter_ = QLineEdit(List)
        self.filter_.setObjectName(u"filter_")
        self.filter_.setClearButtonEnabled(True)

        self.banner.addWidget(self.filter_)

        self.count = QLabel(List)
        self.count.setObjectName(u"count")
        self.count.setText(u"\u2014")

        self.banner.addWidget(self.count)

        self.add_files = QPushButton(List)
        self.add_files.setObjectName(u"add_files")
        self.add_files.setVisible(False)

        self.banner.addWidget(self.add_files)

        self.new = QPushButton(List)
        self.new.setObjectName(u"new")
        self.new.setVisible(False)

        self.banner.addWidget(self.new)


        self.arrangement.addLayout(self.banner)

        self.table = QTableView(List)
        self.table.setObjectName(u"table")
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)

        self.arrangement.addWidget(self.table)


        self.retranslateUi(List)

        QMetaObject.connectSlotsByName(List)
    # setupUi

    def retranslateUi(self, List):
        self.filter_.setPlaceholderText(QCoreApplication.translate("List", u"Filter\u2026", None))
#if QT_CONFIG(tooltip)
        self.add_files.setToolTip(QCoreApplication.translate("List", u"The files are referenced where they are, without a copy, and checked at once; they can also be dropped on the list.", None))
#endif // QT_CONFIG(tooltip)
        pass
    # retranslateUi

