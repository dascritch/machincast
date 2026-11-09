# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'feed_card.ui'
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
from PySide6.QtWidgets import (QApplication, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QSlider, QVBoxLayout,
    QWidget)

class Ui_FeedCard(object):
    def setupUi(self, FeedCard):
        if not FeedCard.objectName():
            FeedCard.setObjectName(u"FeedCard")
        FeedCard.resize(900, 600)
        self.arrangement = QVBoxLayout(FeedCard)
        self.arrangement.setObjectName(u"arrangement")
        self.form = QFormLayout()
        self.form.setObjectName(u"form")
        self.name_caption = QLabel(FeedCard)
        self.name_caption.setObjectName(u"name_caption")

        self.form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.name_caption)

        self.name = QLineEdit(FeedCard)
        self.name.setObjectName(u"name")
        self.name.setMaxLength(255)

        self.form.setWidget(0, QFormLayout.ItemRole.FieldRole, self.name)

        self.url_caption = QLabel(FeedCard)
        self.url_caption.setObjectName(u"url_caption")

        self.form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.url_caption)

        self.url = QLineEdit(FeedCard)
        self.url.setObjectName(u"url")

        self.form.setWidget(1, QFormLayout.ItemRole.FieldRole, self.url)

        self.buffer_caption = QLabel(FeedCard)
        self.buffer_caption.setObjectName(u"buffer_caption")

        self.form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.buffer_caption)

        self.buffer_layout = QHBoxLayout()
        self.buffer_layout.setObjectName(u"buffer_layout")
        self.buffer = QSlider(FeedCard)
        self.buffer.setObjectName(u"buffer")
        self.buffer.setMinimum(2)
        self.buffer.setMaximum(10)
        self.buffer.setPageStep(1)
        self.buffer.setOrientation(Qt.Orientation.Horizontal)
        self.buffer.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.buffer.setTickInterval(1)

        self.buffer_layout.addWidget(self.buffer)

        self.buffer_value = QLabel(FeedCard)
        self.buffer_value.setObjectName(u"buffer_value")

        self.buffer_layout.addWidget(self.buffer_value)

        self.buffer_layout.setStretch(0, 1)

        self.form.setLayout(2, QFormLayout.ItemRole.FieldRole, self.buffer_layout)

        self.buffer_explanation = QLabel(FeedCard)
        self.buffer_explanation.setObjectName(u"buffer_explanation")
        self.buffer_explanation.setWordWrap(True)

        self.form.setWidget(3, QFormLayout.ItemRole.FieldRole, self.buffer_explanation)


        self.arrangement.addLayout(self.form)

        self.trial = QHBoxLayout()
        self.trial.setObjectName(u"trial")
        self.test = QPushButton(FeedCard)
        self.test.setObjectName(u"test")

        self.trial.addWidget(self.test)

        self.trial_result = QLabel(FeedCard)
        self.trial_result.setObjectName(u"trial_result")
        self.trial_result.setWordWrap(True)

        self.trial.addWidget(self.trial_result)

        self.trial.setStretch(1, 1)

        self.arrangement.addLayout(self.trial)

        self.stream_group = QGroupBox(FeedCard)
        self.stream_group.setObjectName(u"stream_group")
        self.stream_layout = QVBoxLayout(self.stream_group)
        self.stream_layout.setObjectName(u"stream_layout")
        self.streams = QListWidget(self.stream_group)
        self.streams.setObjectName(u"streams")
        self.streams.setAlternatingRowColors(True)

        self.stream_layout.addWidget(self.streams)

        self.stream_explanation = QLabel(self.stream_group)
        self.stream_explanation.setObjectName(u"stream_explanation")
        self.stream_explanation.setWordWrap(True)

        self.stream_layout.addWidget(self.stream_explanation)


        self.arrangement.addWidget(self.stream_group)

        self.foot = QHBoxLayout()
        self.foot.setObjectName(u"foot")
        self.delete = QPushButton(FeedCard)
        self.delete.setObjectName(u"delete")

        self.foot.addWidget(self.delete)

        self.message = QLabel(FeedCard)
        self.message.setObjectName(u"message")
        self.message.setWordWrap(True)

        self.foot.addWidget(self.message)

        self.cancel = QPushButton(FeedCard)
        self.cancel.setObjectName(u"cancel")

        self.foot.addWidget(self.cancel)

        self.save = QPushButton(FeedCard)
        self.save.setObjectName(u"save")

        self.foot.addWidget(self.save)

        self.foot.setStretch(1, 1)

        self.arrangement.addLayout(self.foot)

        self.arrangement.setStretch(2, 1)
#if QT_CONFIG(shortcut)
        self.name_caption.setBuddy(self.name)
        self.url_caption.setBuddy(self.url)
        self.buffer_caption.setBuddy(self.buffer)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(FeedCard)

        self.save.setDefault(True)


        QMetaObject.connectSlotsByName(FeedCard)
    # setupUi

    def retranslateUi(self, FeedCard):
        self.name_caption.setText(QCoreApplication.translate("FeedCard", u"&Name", None))
        self.name.setPlaceholderText(QCoreApplication.translate("FeedCard", u"Required, and unique to this feed", None))
        self.url_caption.setText(QCoreApplication.translate("FeedCard", u"A&ddress", None))
        self.url.setPlaceholderText(QCoreApplication.translate("FeedCard", u"https://\u2026: the address of the stream, required", None))
        self.buffer_caption.setText(QCoreApplication.translate("FeedCard", u"&Buffer", None))
        self.buffer_explanation.setText(QCoreApplication.translate("FeedCard", u"The stream waits for its buffer to be full before playing. Short, it starts quickly, but may not be enough for an irregular network; long, it holds better, but takes longer to start and to restart.", None))
        self.test.setText(QCoreApplication.translate("FeedCard", u"Test the stream", None))
        self.stream_group.setTitle(QCoreApplication.translate("FeedCard", u"Streams that follow it", None))
        self.stream_explanation.setText(QCoreApplication.translate("FeedCard", u"These streams play the address of the feed: a new address applies to all. A stream chooses its feed in its card.", None))
        self.delete.setText(QCoreApplication.translate("FeedCard", u"\u274c Delete\u2026", None))
#if QT_CONFIG(tooltip)
        self.delete.setToolTip(QCoreApplication.translate("FeedCard", u"Deletes the element from the database, after confirmation; no file is touched.", None))
#endif // QT_CONFIG(tooltip)
        self.cancel.setText(QCoreApplication.translate("FeedCard", u"Cancel", None))
        self.save.setText(QCoreApplication.translate("FeedCard", u"Save", None))
        pass
    # retranslateUi

