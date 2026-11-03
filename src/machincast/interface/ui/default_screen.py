# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'default_screen.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QFormLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QProgressBar, QPushButton, QSizePolicy, QSpacerItem,
    QTableView, QToolButton, QVBoxLayout, QWidget)

class Ui_DefaultScreen(object):
    def setupUi(self, DefaultScreen):
        if not DefaultScreen.objectName():
            DefaultScreen.setObjectName(u"DefaultScreen")
        DefaultScreen.resize(1100, 760)
        DefaultScreen.setWindowTitle(u"MachinCast")
        self.arrangement = QVBoxLayout(DefaultScreen)
        self.arrangement.setObjectName(u"arrangement")
        self.banner = QHBoxLayout()
        self.banner.setObjectName(u"banner")
        self.hour = QLabel(DefaultScreen)
        self.hour.setObjectName(u"hour")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.hour.setFont(font)
        self.hour.setText(u"\u2014")
        self.hour.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.banner.addWidget(self.hour)

        self.public_text = QLabel(DefaultScreen)
        self.public_text.setObjectName(u"public_text")
        font1 = QFont()
        font1.setPointSize(12)
        font1.setItalic(True)
        self.public_text.setFont(font1)
        self.public_text.setText(u"\u2014")
        self.public_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.public_text.setWordWrap(True)
        self.public_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.banner.addWidget(self.public_text)

        self.playback_state = QLabel(DefaultScreen)
        self.playback_state.setObjectName(u"playback_state")
        font2 = QFont()
        font2.setPointSize(12)
        font2.setBold(True)
        self.playback_state.setFont(font2)
        self.playback_state.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.banner.addWidget(self.playback_state)

        self.banner.setStretch(1, 1)

        self.arrangement.addLayout(self.banner)

        self.on_air_event_line = QHBoxLayout()
        self.on_air_event_line.setObjectName(u"on_air_event_line")
        self.on_air_event = QLabel(DefaultScreen)
        self.on_air_event.setObjectName(u"on_air_event")
        self.on_air_event.setFont(font2)
        self.on_air_event.setText(u"\u2014")
        self.on_air_event.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.on_air_event.setWordWrap(True)

        self.on_air_event_line.addWidget(self.on_air_event)

        self.on_air_event_line.setStretch(0, 1)

        self.arrangement.addLayout(self.on_air_event_line)

        self.sounds = QHBoxLayout()
        self.sounds.setObjectName(u"sounds")
        self.ongoing_frame = QGroupBox(DefaultScreen)
        self.ongoing_frame.setObjectName(u"ongoing_frame")
        self.ongoing_layout = QVBoxLayout(self.ongoing_frame)
        self.ongoing_layout.setObjectName(u"ongoing_layout")
        self.ongoing_timeline_place = QWidget(self.ongoing_frame)
        self.ongoing_timeline_place.setObjectName(u"ongoing_timeline_place")
        self.ongoing_timeline_place.setMinimumSize(QSize(0, 72))

        self.ongoing_layout.addWidget(self.ongoing_timeline_place)

        self.ongoing_progress = QProgressBar(self.ongoing_frame)
        self.ongoing_progress.setObjectName(u"ongoing_progress")
        self.ongoing_progress.setMaximum(100)
        self.ongoing_progress.setValue(0)
        self.ongoing_progress.setFormat(u"\u2014")

        self.ongoing_layout.addWidget(self.ongoing_progress)

        self.ongoing_title_line = QHBoxLayout()
        self.ongoing_title_line.setObjectName(u"ongoing_title_line")
        self.ongoing_title = QLabel(self.ongoing_frame)
        self.ongoing_title.setObjectName(u"ongoing_title")
        font3 = QFont()
        font3.setPointSize(14)
        font3.setBold(True)
        self.ongoing_title.setFont(font3)
        self.ongoing_title.setText(u"\u2014")
        self.ongoing_title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.ongoing_title.setWordWrap(True)

        self.ongoing_title_line.addWidget(self.ongoing_title)

        self.open_ongoing_sound = QToolButton(self.ongoing_frame)
        self.open_ongoing_sound.setObjectName(u"open_ongoing_sound")
        self.open_ongoing_sound.setEnabled(False)

        self.ongoing_title_line.addWidget(self.open_ongoing_sound)

        self.ongoing_title_line.setStretch(0, 1)

        self.ongoing_layout.addLayout(self.ongoing_title_line)

        self.ongoing_form = QFormLayout()
        self.ongoing_form.setObjectName(u"ongoing_form")
        self.ongoing_event_heading = QLabel(self.ongoing_frame)
        self.ongoing_event_heading.setObjectName(u"ongoing_event_heading")

        self.ongoing_form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.ongoing_event_heading)

        self.ongoing_event_line = QHBoxLayout()
        self.ongoing_event_line.setObjectName(u"ongoing_event_line")
        self.ongoing_event = QLabel(self.ongoing_frame)
        self.ongoing_event.setObjectName(u"ongoing_event")
        self.ongoing_event.setText(u"\u2014")
        self.ongoing_event.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.ongoing_event.setWordWrap(True)

        self.ongoing_event_line.addWidget(self.ongoing_event)

        self.open_ongoing_event = QToolButton(self.ongoing_frame)
        self.open_ongoing_event.setObjectName(u"open_ongoing_event")
        self.open_ongoing_event.setEnabled(False)

        self.ongoing_event_line.addWidget(self.open_ongoing_event)

        self.ongoing_event_line.setStretch(0, 1)

        self.ongoing_form.setLayout(0, QFormLayout.ItemRole.FieldRole, self.ongoing_event_line)

        self.ongoing_sequence_heading = QLabel(self.ongoing_frame)
        self.ongoing_sequence_heading.setObjectName(u"ongoing_sequence_heading")

        self.ongoing_form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.ongoing_sequence_heading)

        self.ongoing_sequence_line = QHBoxLayout()
        self.ongoing_sequence_line.setObjectName(u"ongoing_sequence_line")
        self.ongoing_sequence = QLabel(self.ongoing_frame)
        self.ongoing_sequence.setObjectName(u"ongoing_sequence")
        self.ongoing_sequence.setText(u"\u2014")
        self.ongoing_sequence.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.ongoing_sequence.setWordWrap(True)

        self.ongoing_sequence_line.addWidget(self.ongoing_sequence)

        self.open_ongoing_sequence = QToolButton(self.ongoing_frame)
        self.open_ongoing_sequence.setObjectName(u"open_ongoing_sequence")
        self.open_ongoing_sequence.setEnabled(False)

        self.ongoing_sequence_line.addWidget(self.open_ongoing_sequence)

        self.ongoing_sequence_line.setStretch(0, 1)

        self.ongoing_form.setLayout(1, QFormLayout.ItemRole.FieldRole, self.ongoing_sequence_line)

        self.ongoing_bank_heading = QLabel(self.ongoing_frame)
        self.ongoing_bank_heading.setObjectName(u"ongoing_bank_heading")

        self.ongoing_form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.ongoing_bank_heading)

        self.ongoing_bank_line = QHBoxLayout()
        self.ongoing_bank_line.setObjectName(u"ongoing_bank_line")
        self.ongoing_bank = QLabel(self.ongoing_frame)
        self.ongoing_bank.setObjectName(u"ongoing_bank")
        self.ongoing_bank.setText(u"\u2014")
        self.ongoing_bank.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.ongoing_bank.setWordWrap(True)

        self.ongoing_bank_line.addWidget(self.ongoing_bank)

        self.open_ongoing_bank = QToolButton(self.ongoing_frame)
        self.open_ongoing_bank.setObjectName(u"open_ongoing_bank")
        self.open_ongoing_bank.setEnabled(False)

        self.ongoing_bank_line.addWidget(self.open_ongoing_bank)

        self.ongoing_bank_line.setStretch(0, 1)

        self.ongoing_form.setLayout(2, QFormLayout.ItemRole.FieldRole, self.ongoing_bank_line)

        self.ongoing_schedule_heading = QLabel(self.ongoing_frame)
        self.ongoing_schedule_heading.setObjectName(u"ongoing_schedule_heading")

        self.ongoing_form.setWidget(3, QFormLayout.ItemRole.LabelRole, self.ongoing_schedule_heading)

        self.ongoing_schedule = QLabel(self.ongoing_frame)
        self.ongoing_schedule.setObjectName(u"ongoing_schedule")
        self.ongoing_schedule.setText(u"\u2014")
        self.ongoing_schedule.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.ongoing_schedule.setWordWrap(True)

        self.ongoing_form.setWidget(3, QFormLayout.ItemRole.FieldRole, self.ongoing_schedule)

        self.ongoing_location_heading = QLabel(self.ongoing_frame)
        self.ongoing_location_heading.setObjectName(u"ongoing_location_heading")

        self.ongoing_form.setWidget(4, QFormLayout.ItemRole.LabelRole, self.ongoing_location_heading)

        self.ongoing_location = QLineEdit(self.ongoing_frame)
        self.ongoing_location.setObjectName(u"ongoing_location")
        self.ongoing_location.setText(u"\u2014")
        self.ongoing_location.setFrame(False)
        self.ongoing_location.setReadOnly(True)

        self.ongoing_form.setWidget(4, QFormLayout.ItemRole.FieldRole, self.ongoing_location)


        self.ongoing_layout.addLayout(self.ongoing_form)

        self.pack_ongoing = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.ongoing_layout.addItem(self.pack_ongoing)


        self.sounds.addWidget(self.ongoing_frame)

        self.on_air_column = QGroupBox(DefaultScreen)
        self.on_air_column.setObjectName(u"on_air_column")
        self.on_air_column.setMaximumSize(QSize(140, 16777215))
        self.on_air_layout = QVBoxLayout(self.on_air_column)
        self.on_air_layout.setObjectName(u"on_air_layout")
        self.clipping_light = QLabel(self.on_air_column)
        self.clipping_light.setObjectName(u"clipping_light")
        font4 = QFont()
        font4.setPointSize(7)
        self.clipping_light.setFont(font4)
        self.clipping_light.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.on_air_layout.addWidget(self.clipping_light)

        self.vu_meter_place = QWidget(self.on_air_column)
        self.vu_meter_place.setObjectName(u"vu_meter_place")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.vu_meter_place.sizePolicy().hasHeightForWidth())
        self.vu_meter_place.setSizePolicy(sizePolicy)
        self.vu_meter_place.setMinimumSize(QSize(90, 160))

        self.on_air_layout.addWidget(self.vu_meter_place)

        self.dead_air_light = QLabel(self.on_air_column)
        self.dead_air_light.setObjectName(u"dead_air_light")
        self.dead_air_light.setFont(font4)
        self.dead_air_light.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.on_air_layout.addWidget(self.dead_air_light)

        self.monitor_state = QLabel(self.on_air_column)
        self.monitor_state.setObjectName(u"monitor_state")
        self.monitor_state.setWordWrap(True)

        self.on_air_layout.addWidget(self.monitor_state)

        self.on_air_layout.setStretch(1, 1)

        self.sounds.addWidget(self.on_air_column)

        self.next_frame = QGroupBox(DefaultScreen)
        self.next_frame.setObjectName(u"next_frame")
        self.next_layout = QVBoxLayout(self.next_frame)
        self.next_layout.setObjectName(u"next_layout")
        self.next_timeline_place = QWidget(self.next_frame)
        self.next_timeline_place.setObjectName(u"next_timeline_place")
        self.next_timeline_place.setMinimumSize(QSize(0, 72))

        self.next_layout.addWidget(self.next_timeline_place)

        self.next_title_line = QHBoxLayout()
        self.next_title_line.setObjectName(u"next_title_line")
        self.next_title = QLabel(self.next_frame)
        self.next_title.setObjectName(u"next_title")
        self.next_title.setFont(font3)
        self.next_title.setText(u"\u2014")
        self.next_title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.next_title.setWordWrap(True)

        self.next_title_line.addWidget(self.next_title)

        self.open_next_sound = QToolButton(self.next_frame)
        self.open_next_sound.setObjectName(u"open_next_sound")
        self.open_next_sound.setEnabled(False)

        self.next_title_line.addWidget(self.open_next_sound)

        self.next_title_line.setStretch(0, 1)

        self.next_layout.addLayout(self.next_title_line)

        self.next_form = QFormLayout()
        self.next_form.setObjectName(u"next_form")
        self.next_event_heading = QLabel(self.next_frame)
        self.next_event_heading.setObjectName(u"next_event_heading")

        self.next_form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.next_event_heading)

        self.next_event_line = QHBoxLayout()
        self.next_event_line.setObjectName(u"next_event_line")
        self.next_event = QLabel(self.next_frame)
        self.next_event.setObjectName(u"next_event")
        self.next_event.setText(u"\u2014")
        self.next_event.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.next_event.setWordWrap(True)

        self.next_event_line.addWidget(self.next_event)

        self.open_next_event = QToolButton(self.next_frame)
        self.open_next_event.setObjectName(u"open_next_event")
        self.open_next_event.setEnabled(False)

        self.next_event_line.addWidget(self.open_next_event)

        self.next_event_line.setStretch(0, 1)

        self.next_form.setLayout(0, QFormLayout.ItemRole.FieldRole, self.next_event_line)

        self.next_sequence_heading = QLabel(self.next_frame)
        self.next_sequence_heading.setObjectName(u"next_sequence_heading")

        self.next_form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.next_sequence_heading)

        self.next_sequence_line = QHBoxLayout()
        self.next_sequence_line.setObjectName(u"next_sequence_line")
        self.next_sequence = QLabel(self.next_frame)
        self.next_sequence.setObjectName(u"next_sequence")
        self.next_sequence.setText(u"\u2014")
        self.next_sequence.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.next_sequence.setWordWrap(True)

        self.next_sequence_line.addWidget(self.next_sequence)

        self.open_next_sequence = QToolButton(self.next_frame)
        self.open_next_sequence.setObjectName(u"open_next_sequence")
        self.open_next_sequence.setEnabled(False)

        self.next_sequence_line.addWidget(self.open_next_sequence)

        self.next_sequence_line.setStretch(0, 1)

        self.next_form.setLayout(1, QFormLayout.ItemRole.FieldRole, self.next_sequence_line)

        self.next_bank_heading = QLabel(self.next_frame)
        self.next_bank_heading.setObjectName(u"next_bank_heading")

        self.next_form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.next_bank_heading)

        self.next_bank_line = QHBoxLayout()
        self.next_bank_line.setObjectName(u"next_bank_line")
        self.next_bank = QLabel(self.next_frame)
        self.next_bank.setObjectName(u"next_bank")
        self.next_bank.setText(u"\u2014")
        self.next_bank.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.next_bank.setWordWrap(True)

        self.next_bank_line.addWidget(self.next_bank)

        self.open_next_bank = QToolButton(self.next_frame)
        self.open_next_bank.setObjectName(u"open_next_bank")
        self.open_next_bank.setEnabled(False)

        self.next_bank_line.addWidget(self.open_next_bank)

        self.next_bank_line.setStretch(0, 1)

        self.next_form.setLayout(2, QFormLayout.ItemRole.FieldRole, self.next_bank_line)

        self.next_schedule_heading = QLabel(self.next_frame)
        self.next_schedule_heading.setObjectName(u"next_schedule_heading")

        self.next_form.setWidget(3, QFormLayout.ItemRole.LabelRole, self.next_schedule_heading)

        self.next_schedule = QLabel(self.next_frame)
        self.next_schedule.setObjectName(u"next_schedule")
        self.next_schedule.setText(u"\u2014")
        self.next_schedule.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.next_schedule.setWordWrap(True)

        self.next_form.setWidget(3, QFormLayout.ItemRole.FieldRole, self.next_schedule)

        self.next_location_heading = QLabel(self.next_frame)
        self.next_location_heading.setObjectName(u"next_location_heading")

        self.next_form.setWidget(4, QFormLayout.ItemRole.LabelRole, self.next_location_heading)

        self.next_location = QLineEdit(self.next_frame)
        self.next_location.setObjectName(u"next_location")
        self.next_location.setText(u"\u2014")
        self.next_location.setFrame(False)
        self.next_location.setReadOnly(True)

        self.next_form.setWidget(4, QFormLayout.ItemRole.FieldRole, self.next_location)

        self.next_healthy_heading = QLabel(self.next_frame)
        self.next_healthy_heading.setObjectName(u"next_healthy_heading")

        self.next_form.setWidget(5, QFormLayout.ItemRole.LabelRole, self.next_healthy_heading)

        self.next_healthy_line = QHBoxLayout()
        self.next_healthy_line.setObjectName(u"next_healthy_line")
        self.next_healthy = QLabel(self.next_frame)
        self.next_healthy.setObjectName(u"next_healthy")
        self.next_healthy.setText(u"\u2014")
        self.next_healthy.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.next_healthy_line.addWidget(self.next_healthy)

        self.push_listened = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.next_healthy_line.addItem(self.push_listened)

        self.test_next_stream = QPushButton(self.next_frame)
        self.test_next_stream.setObjectName(u"test_next_stream")

        self.next_healthy_line.addWidget(self.test_next_stream)

        self.preview_next = QPushButton(self.next_frame)
        self.preview_next.setObjectName(u"preview_next")

        self.next_healthy_line.addWidget(self.preview_next)


        self.next_form.setLayout(5, QFormLayout.ItemRole.SpanningRole, self.next_healthy_line)

        self.next_stream = QLabel(self.next_frame)
        self.next_stream.setObjectName(u"next_stream")
        self.next_stream.setWordWrap(True)
        self.next_stream.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.next_form.setWidget(6, QFormLayout.ItemRole.SpanningRole, self.next_stream)


        self.next_layout.addLayout(self.next_form)

        self.pack_next = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.next_layout.addItem(self.pack_next)


        self.sounds.addWidget(self.next_frame)

        self.sounds.setStretch(0, 1)
        self.sounds.setStretch(2, 1)

        self.arrangement.addLayout(self.sounds)

        self.upcoming_frame = QGroupBox(DefaultScreen)
        self.upcoming_frame.setObjectName(u"upcoming_frame")
        self.upcoming_layout = QVBoxLayout(self.upcoming_frame)
        self.upcoming_layout.setObjectName(u"upcoming_layout")
        self.upcoming_table = QTableView(self.upcoming_frame)
        self.upcoming_table.setObjectName(u"upcoming_table")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.upcoming_table.sizePolicy().hasHeightForWidth())
        self.upcoming_table.setSizePolicy(sizePolicy1)
        self.upcoming_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.upcoming_table.setAlternatingRowColors(True)
        self.upcoming_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.upcoming_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.upcoming_table.horizontalHeader().setStretchLastSection(True)
        self.upcoming_table.verticalHeader().setVisible(False)

        self.upcoming_layout.addWidget(self.upcoming_table)


        self.arrangement.addWidget(self.upcoming_frame)

        self.airplay_frame = QGroupBox(DefaultScreen)
        self.airplay_frame.setObjectName(u"airplay_frame")
        self.airplay_layout = QVBoxLayout(self.airplay_frame)
        self.airplay_layout.setObjectName(u"airplay_layout")
        self.table_airplay = QTableView(self.airplay_frame)
        self.table_airplay.setObjectName(u"table_airplay")
        self.table_airplay.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_airplay.setAlternatingRowColors(True)
        self.table_airplay.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_airplay.horizontalHeader().setStretchLastSection(True)
        self.table_airplay.verticalHeader().setVisible(False)

        self.airplay_layout.addWidget(self.table_airplay)


        self.arrangement.addWidget(self.airplay_frame)


        self.retranslateUi(DefaultScreen)

        QMetaObject.connectSlotsByName(DefaultScreen)
    # setupUi

    def retranslateUi(self, DefaultScreen):
#if QT_CONFIG(tooltip)
        self.public_text.setToolTip(QCoreApplication.translate("DefaultScreen", u"What the public outputs show of the current sound", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.playback_state.setToolTip(QCoreApplication.translate("DefaultScreen", u"State of Machin player", None))
#endif // QT_CONFIG(tooltip)
        self.playback_state.setText(QCoreApplication.translate("DefaultScreen", u"Stopped", None))
#if QT_CONFIG(tooltip)
        self.on_air_event.setToolTip(QCoreApplication.translate("DefaultScreen", u"Event on air", None))
#endif // QT_CONFIG(tooltip)
        self.ongoing_frame.setTitle(QCoreApplication.translate("DefaultScreen", u"Current sound", None))
#if QT_CONFIG(tooltip)
        self.ongoing_timeline_place.setToolTip(QCoreApplication.translate("DefaultScreen", u"Waveform, silences and fades of the current sound, as the broadcast plays it", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.open_ongoing_sound.setToolTip(QCoreApplication.translate("DefaultScreen", u"Open the card of the sound", None))
#endif // QT_CONFIG(tooltip)
        self.open_ongoing_sound.setText(QCoreApplication.translate("DefaultScreen", u"Card\u2026", None))
        self.ongoing_event_heading.setText(QCoreApplication.translate("DefaultScreen", u"Event", None))
#if QT_CONFIG(tooltip)
        self.open_ongoing_event.setToolTip(QCoreApplication.translate("DefaultScreen", u"Open the card of the event", None))
#endif // QT_CONFIG(tooltip)
        self.open_ongoing_event.setText(QCoreApplication.translate("DefaultScreen", u"Card\u2026", None))
        self.ongoing_sequence_heading.setText(QCoreApplication.translate("DefaultScreen", u"Sequence", None))
#if QT_CONFIG(tooltip)
        self.open_ongoing_sequence.setToolTip(QCoreApplication.translate("DefaultScreen", u"Open the card of the sequence", None))
#endif // QT_CONFIG(tooltip)
        self.open_ongoing_sequence.setText(QCoreApplication.translate("DefaultScreen", u"Card\u2026", None))
        self.ongoing_bank_heading.setText(QCoreApplication.translate("DefaultScreen", u"Bank", None))
#if QT_CONFIG(tooltip)
        self.open_ongoing_bank.setToolTip(QCoreApplication.translate("DefaultScreen", u"Open the card of the bank", None))
#endif // QT_CONFIG(tooltip)
        self.open_ongoing_bank.setText(QCoreApplication.translate("DefaultScreen", u"Card\u2026", None))
        self.ongoing_schedule_heading.setText(QCoreApplication.translate("DefaultScreen", u"Time", None))
        self.ongoing_location_heading.setText(QCoreApplication.translate("DefaultScreen", u"Location", None))
        self.on_air_column.setTitle(QCoreApplication.translate("DefaultScreen", u"On air", None))
#if QT_CONFIG(tooltip)
        self.clipping_light.setToolTip(QCoreApplication.translate("DefaultScreen", u"A peak at -1 dBFS or more, in the last 3 seconds", None))
#endif // QT_CONFIG(tooltip)
        self.clipping_light.setText(QCoreApplication.translate("DefaultScreen", u"Clipping", None))
#if QT_CONFIG(tooltip)
        self.dead_air_light.setToolTip(QCoreApplication.translate("DefaultScreen", u"More than 5 seconds below -50 dBFS", None))
#endif // QT_CONFIG(tooltip)
        self.dead_air_light.setText(QCoreApplication.translate("DefaultScreen", u"Dead air", None))
        self.monitor_state.setText("")
        self.next_frame.setTitle(QCoreApplication.translate("DefaultScreen", u"Next sound", None))
#if QT_CONFIG(tooltip)
        self.next_timeline_place.setToolTip(QCoreApplication.translate("DefaultScreen", u"Waveform, silences and fades of the next sound, as the broadcast will play it", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.open_next_sound.setToolTip(QCoreApplication.translate("DefaultScreen", u"Open the card of the sound", None))
#endif // QT_CONFIG(tooltip)
        self.open_next_sound.setText(QCoreApplication.translate("DefaultScreen", u"Card\u2026", None))
        self.next_event_heading.setText(QCoreApplication.translate("DefaultScreen", u"Event", None))
#if QT_CONFIG(tooltip)
        self.open_next_event.setToolTip(QCoreApplication.translate("DefaultScreen", u"Open the card of the event", None))
#endif // QT_CONFIG(tooltip)
        self.open_next_event.setText(QCoreApplication.translate("DefaultScreen", u"Card\u2026", None))
        self.next_sequence_heading.setText(QCoreApplication.translate("DefaultScreen", u"Sequence", None))
#if QT_CONFIG(tooltip)
        self.open_next_sequence.setToolTip(QCoreApplication.translate("DefaultScreen", u"Open the card of the sequence", None))
#endif // QT_CONFIG(tooltip)
        self.open_next_sequence.setText(QCoreApplication.translate("DefaultScreen", u"Card\u2026", None))
        self.next_bank_heading.setText(QCoreApplication.translate("DefaultScreen", u"Bank", None))
#if QT_CONFIG(tooltip)
        self.open_next_bank.setToolTip(QCoreApplication.translate("DefaultScreen", u"Open the card of the bank", None))
#endif // QT_CONFIG(tooltip)
        self.open_next_bank.setText(QCoreApplication.translate("DefaultScreen", u"Card\u2026", None))
        self.next_schedule_heading.setText(QCoreApplication.translate("DefaultScreen", u"Estimated time", None))
        self.next_location_heading.setText(QCoreApplication.translate("DefaultScreen", u"Location", None))
        self.next_healthy_heading.setText(QCoreApplication.translate("DefaultScreen", u"Healthy", None))
#if QT_CONFIG(tooltip)
        self.test_next_stream.setToolTip(QCoreApplication.translate("DefaultScreen", u"Connect to the stream of the next sound, without playing anything: does it receive sound, of what type, at what bitrate?", None))
#endif // QT_CONFIG(tooltip)
        self.test_next_stream.setText(QCoreApplication.translate("DefaultScreen", u"Test the stream connection", None))
#if QT_CONFIG(tooltip)
        self.preview_next.setToolTip(QCoreApplication.translate("DefaultScreen", u"Listen to the next sound on the pre-listen output, never on air", None))
#endif // QT_CONFIG(tooltip)
        self.preview_next.setText(QCoreApplication.translate("DefaultScreen", u"Pre-listen", None))
        self.upcoming_frame.setTitle(QCoreApplication.translate("DefaultScreen", u"Coming after the next sound", None))
#if QT_CONFIG(tooltip)
        self.upcoming_table.setToolTip(QCoreApplication.translate("DefaultScreen", u"The sounds planned after the next one, the furthest at the top. Double-click on a sound, an event, a sequence or a bank: open its card", None))
#endif // QT_CONFIG(tooltip)
        self.airplay_frame.setTitle(QCoreApplication.translate("DefaultScreen", u"Airplay: the last 10 sounds", None))
#if QT_CONFIG(tooltip)
        self.table_airplay.setToolTip(QCoreApplication.translate("DefaultScreen", u"Double-click on a sound, an event, a sequence or a bank: open its card", None))
#endif // QT_CONFIG(tooltip)
        pass
    # retranslateUi

