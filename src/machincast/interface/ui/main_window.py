# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
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
from PySide6.QtWidgets import (QApplication, QMainWindow, QSizePolicy, QStatusBar,
    QTabWidget, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1100, 800)
        self.centre = QWidget(MainWindow)
        self.centre.setObjectName(u"centre")
        self.arrangement = QVBoxLayout(self.centre)
        self.arrangement.setObjectName(u"arrangement")
        self.tabs = QTabWidget(self.centre)
        self.tabs.setObjectName(u"tabs")
        self.tabs.setDocumentMode(True)

        self.arrangement.addWidget(self.tabs)

        MainWindow.setCentralWidget(self.centre)
        self.state_bar = QStatusBar(MainWindow)
        self.state_bar.setObjectName(u"state_bar")
        MainWindow.setStatusBar(self.state_bar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MachinCast", None))
    # retranslateUi

