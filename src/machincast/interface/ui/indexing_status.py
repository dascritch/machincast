# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'indexing_status.ui'
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
from PySide6.QtWidgets import (QApplication, QFormLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget)

class Ui_StatusWindow(object):
    def setupUi(self, StatusWindow):
        if not StatusWindow.objectName():
            StatusWindow.setObjectName(u"StatusWindow")
        StatusWindow.resize(640, 520)
        self.arrangement = QVBoxLayout(StatusWindow)
        self.arrangement.setObjectName(u"arrangement")
        self.counts = QFormLayout()
        self.counts.setObjectName(u"counts")
        self.to_scan_caption = QLabel(StatusWindow)
        self.to_scan_caption.setObjectName(u"to_scan_caption")

        self.counts.setWidget(0, QFormLayout.ItemRole.LabelRole, self.to_scan_caption)

        self.to_scan = QLabel(StatusWindow)
        self.to_scan.setObjectName(u"to_scan")

        self.counts.setWidget(0, QFormLayout.ItemRole.FieldRole, self.to_scan)

        self.scanned_caption = QLabel(StatusWindow)
        self.scanned_caption.setObjectName(u"scanned_caption")

        self.counts.setWidget(1, QFormLayout.ItemRole.LabelRole, self.scanned_caption)

        self.scanned = QLabel(StatusWindow)
        self.scanned.setObjectName(u"scanned")

        self.counts.setWidget(1, QFormLayout.ItemRole.FieldRole, self.scanned)

        self.found_caption = QLabel(StatusWindow)
        self.found_caption.setObjectName(u"found_caption")

        self.counts.setWidget(2, QFormLayout.ItemRole.LabelRole, self.found_caption)

        self.found = QLabel(StatusWindow)
        self.found.setObjectName(u"found")

        self.counts.setWidget(2, QFormLayout.ItemRole.FieldRole, self.found)

        self.summary_caption = QLabel(StatusWindow)
        self.summary_caption.setObjectName(u"summary_caption")

        self.counts.setWidget(3, QFormLayout.ItemRole.LabelRole, self.summary_caption)

        self.summary = QLabel(StatusWindow)
        self.summary.setObjectName(u"summary")

        self.counts.setWidget(3, QFormLayout.ItemRole.FieldRole, self.summary)

        self.complete_caption = QLabel(StatusWindow)
        self.complete_caption.setObjectName(u"complete_caption")

        self.counts.setWidget(4, QFormLayout.ItemRole.LabelRole, self.complete_caption)

        self.complete = QLabel(StatusWindow)
        self.complete.setObjectName(u"complete")

        self.counts.setWidget(4, QFormLayout.ItemRole.FieldRole, self.complete)


        self.arrangement.addLayout(self.counts)

        self.charts = QHBoxLayout()
        self.charts.setObjectName(u"charts")

        self.arrangement.addLayout(self.charts)

        self.foot = QHBoxLayout()
        self.foot.setObjectName(u"foot")
        self.since = QLabel(StatusWindow)
        self.since.setObjectName(u"since")
        self.since.setWordWrap(True)

        self.foot.addWidget(self.since)

        self.shut_down = QPushButton(StatusWindow)
        self.shut_down.setObjectName(u"shut_down")

        self.foot.addWidget(self.shut_down)


        self.arrangement.addLayout(self.foot)


        self.retranslateUi(StatusWindow)

        QMetaObject.connectSlotsByName(StatusWindow)
    # setupUi

    def retranslateUi(self, StatusWindow):
        StatusWindow.setWindowTitle(QCoreApplication.translate("StatusWindow", u"Indexing status", None))
        self.to_scan_caption.setText(QCoreApplication.translate("StatusWindow", u"Directories to scan", None))
        self.scanned_caption.setText(QCoreApplication.translate("StatusWindow", u"Directories scanned", None))
        self.found_caption.setText(QCoreApplication.translate("StatusWindow", u"Sounds found", None))
        self.summary_caption.setText(QCoreApplication.translate("StatusWindow", u"Sounds with a quick indexing", None))
        self.complete_caption.setText(QCoreApplication.translate("StatusWindow", u"Sounds with a full audit", None))
        self.shut_down.setText(QCoreApplication.translate("StatusWindow", u"Close", None))
    # retranslateUi

