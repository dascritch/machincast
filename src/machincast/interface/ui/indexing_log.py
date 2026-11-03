# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'indexing_log.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget)

class Ui_LogWindow(object):
    def setupUi(self, LogWindow):
        if not LogWindow.objectName():
            LogWindow.setObjectName(u"LogWindow")
        LogWindow.resize(900, 500)
        self.arrangement = QVBoxLayout(LogWindow)
        self.arrangement.setObjectName(u"arrangement")
        self.log = QPlainTextEdit(LogWindow)
        self.log.setObjectName(u"log")
        self.log.setReadOnly(True)
        self.log.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.arrangement.addWidget(self.log)

        self.foot = QHBoxLayout()
        self.foot.setObjectName(u"foot")
        self.conclusion = QLabel(LogWindow)
        self.conclusion.setObjectName(u"conclusion")
        self.conclusion.setWordWrap(True)
        self.conclusion.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.foot.addWidget(self.conclusion)

        self.shut_down = QPushButton(LogWindow)
        self.shut_down.setObjectName(u"shut_down")

        self.foot.addWidget(self.shut_down)


        self.arrangement.addLayout(self.foot)


        self.retranslateUi(LogWindow)

        QMetaObject.connectSlotsByName(LogWindow)
    # setupUi

    def retranslateUi(self, LogWindow):
        LogWindow.setWindowTitle(QCoreApplication.translate("LogWindow", u"Indexing", None))
        self.shut_down.setText(QCoreApplication.translate("LogWindow", u"Close", None))
    # retranslateUi

