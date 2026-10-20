# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'journal_indexation.ui'
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

class Ui_FenetreJournal(object):
    def setupUi(self, FenetreJournal):
        if not FenetreJournal.objectName():
            FenetreJournal.setObjectName(u"FenetreJournal")
        FenetreJournal.resize(900, 500)
        self.disposition = QVBoxLayout(FenetreJournal)
        self.disposition.setObjectName(u"disposition")
        self.journal = QPlainTextEdit(FenetreJournal)
        self.journal.setObjectName(u"journal")
        self.journal.setReadOnly(True)
        self.journal.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.disposition.addWidget(self.journal)

        self.pied = QHBoxLayout()
        self.pied.setObjectName(u"pied")
        self.conclusion = QLabel(FenetreJournal)
        self.conclusion.setObjectName(u"conclusion")
        self.conclusion.setWordWrap(True)
        self.conclusion.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.pied.addWidget(self.conclusion)

        self.fermer = QPushButton(FenetreJournal)
        self.fermer.setObjectName(u"fermer")

        self.pied.addWidget(self.fermer)


        self.disposition.addLayout(self.pied)


        self.retranslateUi(FenetreJournal)

        QMetaObject.connectSlotsByName(FenetreJournal)
    # setupUi

    def retranslateUi(self, FenetreJournal):
        FenetreJournal.setWindowTitle(QCoreApplication.translate("FenetreJournal", u"Indexation", None))
        self.fermer.setText(QCoreApplication.translate("FenetreJournal", u"Fermer", None))
    # retranslateUi

