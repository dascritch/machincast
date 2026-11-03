# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'sound_cards.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFormLayout, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QWidget)

class Ui_SoundCards(object):
    def setupUi(self, SoundCards):
        if not SoundCards.objectName():
            SoundCards.setObjectName(u"SoundCards")
        self.form = QFormLayout(SoundCards)
        self.form.setObjectName(u"form")
        self.form.setContentsMargins(0, 0, 0, 0)
        self.output_caption = QLabel(SoundCards)
        self.output_caption.setObjectName(u"output_caption")

        self.form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.output_caption)

        self.output = QComboBox(SoundCards)
        self.output.setObjectName(u"output")

        self.form.setWidget(0, QFormLayout.ItemRole.FieldRole, self.output)

        self.on_air_caption = QLabel(SoundCards)
        self.on_air_caption.setObjectName(u"on_air_caption")

        self.form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.on_air_caption)

        self.on_air_line = QHBoxLayout()
        self.on_air_line.setObjectName(u"on_air_line")
        self.on_air = QComboBox(SoundCards)
        self.on_air.setObjectName(u"on_air")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.on_air.sizePolicy().hasHeightForWidth())
        self.on_air.setSizePolicy(sizePolicy)

        self.on_air_line.addWidget(self.on_air)

        self.test_on_air = QPushButton(SoundCards)
        self.test_on_air.setObjectName(u"test_on_air")

        self.on_air_line.addWidget(self.test_on_air)


        self.form.setLayout(1, QFormLayout.ItemRole.FieldRole, self.on_air_line)

        self.preview_caption = QLabel(SoundCards)
        self.preview_caption.setObjectName(u"preview_caption")

        self.form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.preview_caption)

        self.preview_line = QHBoxLayout()
        self.preview_line.setObjectName(u"preview_line")
        self.preview = QComboBox(SoundCards)
        self.preview.setObjectName(u"preview")
        sizePolicy.setHeightForWidth(self.preview.sizePolicy().hasHeightForWidth())
        self.preview.setSizePolicy(sizePolicy)

        self.preview_line.addWidget(self.preview)

        self.test_preview = QPushButton(SoundCards)
        self.test_preview.setObjectName(u"test_preview")

        self.preview_line.addWidget(self.test_preview)


        self.form.setLayout(2, QFormLayout.ItemRole.FieldRole, self.preview_line)

        self.trial = QLabel(SoundCards)
        self.trial.setObjectName(u"trial")
        self.trial.setWordWrap(True)

        self.form.setWidget(3, QFormLayout.ItemRole.SpanningRole, self.trial)

#if QT_CONFIG(shortcut)
        self.output_caption.setBuddy(self.output)
        self.on_air_caption.setBuddy(self.on_air)
        self.preview_caption.setBuddy(self.preview)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(SoundCards)

        QMetaObject.connectSlotsByName(SoundCards)
    # setupUi

    def retranslateUi(self, SoundCards):
        self.output_caption.setText(QCoreApplication.translate("SoundCards", u"&Type de sortie", None))
#if QT_CONFIG(tooltip)
        self.output.setToolTip(QCoreApplication.translate("SoundCards", u"Le serveur audio par lequel passent l'antenne et la pr\u00e9-\u00e9coute", None))
#endif // QT_CONFIG(tooltip)
        self.on_air_caption.setText(QCoreApplication.translate("SoundCards", u"&Antenne", None))
#if QT_CONFIG(tooltip)
        self.on_air.setToolTip(QCoreApplication.translate("SoundCards", u"La carte son sur laquelle Machin player diffuse l'antenne", None))
#endif // QT_CONFIG(tooltip)
        self.test_on_air.setText(QCoreApplication.translate("SoundCards", u"Tester", None))
        self.preview_caption.setText(QCoreApplication.translate("SoundCards", u"&Pr\u00e9-\u00e9coute", None))
#if QT_CONFIG(tooltip)
        self.preview.setToolTip(QCoreApplication.translate("SoundCards", u"La carte son de la pr\u00e9-\u00e9coute de l'interface, jamais celle de l'antenne", None))
#endif // QT_CONFIG(tooltip)
        self.test_preview.setText(QCoreApplication.translate("SoundCards", u"Tester", None))
        pass
    # retranslateUi

