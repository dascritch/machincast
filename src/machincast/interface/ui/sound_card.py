# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'sound_card.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QDateTimeEdit, QDoubleSpinBox, QFormLayout, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QRadioButton, QScrollArea,
    QSizePolicy, QSpacerItem, QSpinBox, QTableWidget,
    QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

from machincast.interface.slider import DurationSlider

class Ui_SoundCard(object):
    def setupUi(self, SoundCard):
        if not SoundCard.objectName():
            SoundCard.setObjectName(u"SoundCard")
        SoundCard.resize(1100, 760)
        self.arrangement = QVBoxLayout(SoundCard)
        self.arrangement.setObjectName(u"arrangement")
        self.timeline_place = QWidget(SoundCard)
        self.timeline_place.setObjectName(u"timeline_place")

        self.arrangement.addWidget(self.timeline_place)

        self.body = QHBoxLayout()
        self.body.setObjectName(u"body")
        self.scrolling = QScrollArea(SoundCard)
        self.scrolling.setObjectName(u"scrolling")
        self.scrolling.setWidgetResizable(True)
        self.content = QWidget()
        self.content.setObjectName(u"content")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setObjectName(u"content_layout")
        self.sound_group = QGroupBox(self.content)
        self.sound_group.setObjectName(u"sound_group")
        self.sound_form = QFormLayout(self.sound_group)
        self.sound_form.setObjectName(u"sound_form")
        self.type_caption = QLabel(self.sound_group)
        self.type_caption.setObjectName(u"type_caption")

        self.sound_form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.type_caption)

        self.sound_type = QLabel(self.sound_group)
        self.sound_type.setObjectName(u"sound_type")

        self.sound_form.setWidget(0, QFormLayout.ItemRole.FieldRole, self.sound_type)

        self.location_caption = QLabel(self.sound_group)
        self.location_caption.setObjectName(u"location_caption")

        self.sound_form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.location_caption)

        self.location_line = QHBoxLayout()
        self.location_line.setObjectName(u"location_line")
        self.location = QLineEdit(self.sound_group)
        self.location.setObjectName(u"location")
        self.location.setReadOnly(True)

        self.location_line.addWidget(self.location)

        self.open_folder = QToolButton(self.sound_group)
        self.open_folder.setObjectName(u"open_folder")
        icon = QIcon(QIcon.fromTheme(u"folder-open"))
        self.open_folder.setIcon(icon)

        self.location_line.addWidget(self.open_folder)


        self.sound_form.setLayout(1, QFormLayout.ItemRole.FieldRole, self.location_line)

        self.duration_caption = QLabel(self.sound_group)
        self.duration_caption.setObjectName(u"duration_caption")

        self.sound_form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.duration_caption)

        self.duration = QLabel(self.sound_group)
        self.duration.setObjectName(u"duration")

        self.sound_form.setWidget(2, QFormLayout.ItemRole.FieldRole, self.duration)

        self.state_caption = QLabel(self.sound_group)
        self.state_caption.setObjectName(u"state_caption")

        self.sound_form.setWidget(3, QFormLayout.ItemRole.LabelRole, self.state_caption)

        self.state = QComboBox(self.sound_group)
        self.state.setObjectName(u"state")

        self.sound_form.setWidget(3, QFormLayout.ItemRole.FieldRole, self.state)


        self.content_layout.addWidget(self.sound_group)

        self.stream_group = QGroupBox(self.content)
        self.stream_group.setObjectName(u"stream_group")
        self.stream_grid = QGridLayout(self.stream_group)
        self.stream_grid.setObjectName(u"stream_grid")
        self.by_address = QRadioButton(self.stream_group)
        self.by_address.setObjectName(u"by_address")

        self.stream_grid.addWidget(self.by_address, 0, 0, 1, 1)

        self.url_stream = QLineEdit(self.stream_group)
        self.url_stream.setObjectName(u"url_stream")

        self.stream_grid.addWidget(self.url_stream, 0, 1, 1, 1)

        self.by_feed = QRadioButton(self.stream_group)
        self.by_feed.setObjectName(u"by_feed")

        self.stream_grid.addWidget(self.by_feed, 1, 0, 1, 1)

        self.feed = QComboBox(self.stream_group)
        self.feed.setObjectName(u"feed")

        self.stream_grid.addWidget(self.feed, 1, 1, 1, 1)

        self.fallback_caption = QLabel(self.stream_group)
        self.fallback_caption.setObjectName(u"fallback_caption")

        self.stream_grid.addWidget(self.fallback_caption, 2, 0, 1, 1)

        self.fallback = QComboBox(self.stream_group)
        self.fallback.setObjectName(u"fallback")

        self.stream_grid.addWidget(self.fallback, 2, 1, 1, 1)

        self.test = QPushButton(self.stream_group)
        self.test.setObjectName(u"test")

        self.stream_grid.addWidget(self.test, 3, 0, 1, 1)

        self.trial_result = QLabel(self.stream_group)
        self.trial_result.setObjectName(u"trial_result")
        self.trial_result.setWordWrap(True)

        self.stream_grid.addWidget(self.trial_result, 3, 1, 1, 1)


        self.content_layout.addWidget(self.stream_group)

        self.metadata_group = QGroupBox(self.content)
        self.metadata_group.setObjectName(u"metadata_group")
        self.metadata_form = QFormLayout(self.metadata_group)
        self.metadata_form.setObjectName(u"metadata_form")
        self.artist_caption = QLabel(self.metadata_group)
        self.artist_caption.setObjectName(u"artist_caption")

        self.metadata_form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.artist_caption)

        self.artist = QLineEdit(self.metadata_group)
        self.artist.setObjectName(u"artist")
        self.artist.setMaxLength(255)

        self.metadata_form.setWidget(0, QFormLayout.ItemRole.FieldRole, self.artist)

        self.title_caption = QLabel(self.metadata_group)
        self.title_caption.setObjectName(u"title_caption")

        self.metadata_form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.title_caption)

        self.title = QLineEdit(self.metadata_group)
        self.title.setObjectName(u"title")
        self.title.setMaxLength(255)

        self.metadata_form.setWidget(1, QFormLayout.ItemRole.FieldRole, self.title)

        self.year_caption = QLabel(self.metadata_group)
        self.year_caption.setObjectName(u"year_caption")

        self.metadata_form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.year_caption)

        self.year = QLineEdit(self.metadata_group)
        self.year.setObjectName(u"year")
        self.year.setMaxLength(4)

        self.metadata_form.setWidget(2, QFormLayout.ItemRole.FieldRole, self.year)

        self.album_caption = QLabel(self.metadata_group)
        self.album_caption.setObjectName(u"album_caption")

        self.metadata_form.setWidget(3, QFormLayout.ItemRole.LabelRole, self.album_caption)

        self.album = QLineEdit(self.metadata_group)
        self.album.setObjectName(u"album")
        self.album.setMaxLength(255)

        self.metadata_form.setWidget(3, QFormLayout.ItemRole.FieldRole, self.album)

        self.album_artist_caption = QLabel(self.metadata_group)
        self.album_artist_caption.setObjectName(u"album_artist_caption")

        self.metadata_form.setWidget(4, QFormLayout.ItemRole.LabelRole, self.album_artist_caption)

        self.album_artist = QLineEdit(self.metadata_group)
        self.album_artist.setObjectName(u"album_artist")
        self.album_artist.setMaxLength(255)

        self.metadata_form.setWidget(4, QFormLayout.ItemRole.FieldRole, self.album_artist)

        self.category_caption = QLabel(self.metadata_group)
        self.category_caption.setObjectName(u"category_caption")

        self.metadata_form.setWidget(5, QFormLayout.ItemRole.LabelRole, self.category_caption)

        self.genre = QLineEdit(self.metadata_group)
        self.genre.setObjectName(u"genre")
        self.genre.setMaxLength(255)

        self.metadata_form.setWidget(5, QFormLayout.ItemRole.FieldRole, self.genre)

        self.composer_caption = QLabel(self.metadata_group)
        self.composer_caption.setObjectName(u"composer_caption")

        self.metadata_form.setWidget(6, QFormLayout.ItemRole.LabelRole, self.composer_caption)

        self.composer = QLineEdit(self.metadata_group)
        self.composer.setObjectName(u"composer")
        self.composer.setMaxLength(255)

        self.metadata_form.setWidget(6, QFormLayout.ItemRole.FieldRole, self.composer)

        self.label_caption = QLabel(self.metadata_group)
        self.label_caption.setObjectName(u"label_caption")

        self.metadata_form.setWidget(7, QFormLayout.ItemRole.LabelRole, self.label_caption)

        self.label = QLineEdit(self.metadata_group)
        self.label.setObjectName(u"label")
        self.label.setMaxLength(255)

        self.metadata_form.setWidget(7, QFormLayout.ItemRole.FieldRole, self.label)

        self.track_caption = QLabel(self.metadata_group)
        self.track_caption.setObjectName(u"track_caption")

        self.metadata_form.setWidget(8, QFormLayout.ItemRole.LabelRole, self.track_caption)

        self.track = QLineEdit(self.metadata_group)
        self.track.setObjectName(u"track")
        self.track.setMaxLength(4)

        self.metadata_form.setWidget(8, QFormLayout.ItemRole.FieldRole, self.track)

        self.other_caption = QLabel(self.metadata_group)
        self.other_caption.setObjectName(u"other_caption")

        self.metadata_form.setWidget(9, QFormLayout.ItemRole.LabelRole, self.other_caption)

        self.other_metadata = QLabel(self.metadata_group)
        self.other_metadata.setObjectName(u"other_metadata")
        self.other_metadata.setWordWrap(True)

        self.metadata_form.setWidget(9, QFormLayout.ItemRole.FieldRole, self.other_metadata)


        self.content_layout.addWidget(self.metadata_group)

        self.broadcast_group = QGroupBox(self.content)
        self.broadcast_group.setObjectName(u"broadcast_group")
        self.broadcast_form = QFormLayout(self.broadcast_group)
        self.broadcast_form.setObjectName(u"broadcast_form")
        self.hiding_caption = QLabel(self.broadcast_group)
        self.hiding_caption.setObjectName(u"hiding_caption")

        self.broadcast_form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.hiding_caption)

        self.hiding = QComboBox(self.broadcast_group)
        self.hiding.setObjectName(u"hiding")

        self.broadcast_form.setWidget(0, QFormLayout.ItemRole.FieldRole, self.hiding)

        self.has_start = QCheckBox(self.broadcast_group)
        self.has_start.setObjectName(u"has_start")

        self.broadcast_form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.has_start)

        self.broadcast_start = QDateTimeEdit(self.broadcast_group)
        self.broadcast_start.setObjectName(u"broadcast_start")
        self.broadcast_start.setDisplayFormat(u"dd/MM/yyyy HH:mm")
        self.broadcast_start.setCalendarPopup(True)
        self.broadcast_start.setEnabled(False)

        self.broadcast_form.setWidget(1, QFormLayout.ItemRole.FieldRole, self.broadcast_start)

        self.has_end = QCheckBox(self.broadcast_group)
        self.has_end.setObjectName(u"has_end")

        self.broadcast_form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.has_end)

        self.broadcast_end = QDateTimeEdit(self.broadcast_group)
        self.broadcast_end.setObjectName(u"broadcast_end")
        self.broadcast_end.setDisplayFormat(u"dd/MM/yyyy HH:mm")
        self.broadcast_end.setCalendarPopup(True)
        self.broadcast_end.setEnabled(False)

        self.broadcast_form.setWidget(2, QFormLayout.ItemRole.FieldRole, self.broadcast_end)

        self.playback_max_caption = QLabel(self.broadcast_group)
        self.playback_max_caption.setObjectName(u"playback_max_caption")

        self.broadcast_form.setWidget(3, QFormLayout.ItemRole.LabelRole, self.playback_max_caption)

        self.playback_max = QSpinBox(self.broadcast_group)
        self.playback_max.setObjectName(u"playback_max")
        self.playback_max.setMaximum(1000000)

        self.broadcast_form.setWidget(3, QFormLayout.ItemRole.FieldRole, self.playback_max)


        self.content_layout.addWidget(self.broadcast_group)

        self.silence_group = QGroupBox(self.content)
        self.silence_group.setObjectName(u"silence_group")
        self.silence_form = QFormLayout(self.silence_group)
        self.silence_form.setObjectName(u"silence_form")
        self.detection_silences = QCheckBox(self.silence_group)
        self.detection_silences.setObjectName(u"detection_silences")

        self.silence_form.setWidget(0, QFormLayout.ItemRole.SpanningRole, self.detection_silences)

        self.has_detected_start = QCheckBox(self.silence_group)
        self.has_detected_start.setObjectName(u"has_detected_start")

        self.silence_form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.has_detected_start)

        self.detected_start = QDoubleSpinBox(self.silence_group)
        self.detected_start.setObjectName(u"detected_start")
        self.detected_start.setEnabled(False)
        self.detected_start.setSuffix(u" s")
        self.detected_start.setDecimals(2)
        self.detected_start.setMaximum(86400.000000000000000)
        self.detected_start.setSingleStep(0.010000000000000)

        self.silence_form.setWidget(1, QFormLayout.ItemRole.FieldRole, self.detected_start)

        self.has_detected_end = QCheckBox(self.silence_group)
        self.has_detected_end.setObjectName(u"has_detected_end")

        self.silence_form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.has_detected_end)

        self.detected_end = QDoubleSpinBox(self.silence_group)
        self.detected_end.setObjectName(u"detected_end")
        self.detected_end.setEnabled(False)
        self.detected_end.setSuffix(u" s")
        self.detected_end.setDecimals(2)
        self.detected_end.setMaximum(86400.000000000000000)
        self.detected_end.setSingleStep(0.010000000000000)

        self.silence_form.setWidget(2, QFormLayout.ItemRole.FieldRole, self.detected_end)

        self.has_start_crossfade = QCheckBox(self.silence_group)
        self.has_start_crossfade.setObjectName(u"has_start_crossfade")

        self.silence_form.setWidget(3, QFormLayout.ItemRole.LabelRole, self.has_start_crossfade)

        self.start_crossfade = DurationSlider(self.silence_group)
        self.start_crossfade.setObjectName(u"start_crossfade")
        self.start_crossfade.setEnabled(False)

        self.silence_form.setWidget(3, QFormLayout.ItemRole.FieldRole, self.start_crossfade)

        self.has_end_crossfade = QCheckBox(self.silence_group)
        self.has_end_crossfade.setObjectName(u"has_end_crossfade")

        self.silence_form.setWidget(4, QFormLayout.ItemRole.LabelRole, self.has_end_crossfade)

        self.end_crossfade = DurationSlider(self.silence_group)
        self.end_crossfade.setObjectName(u"end_crossfade")
        self.end_crossfade.setEnabled(False)

        self.silence_form.setWidget(4, QFormLayout.ItemRole.FieldRole, self.end_crossfade)


        self.content_layout.addWidget(self.silence_group)

        self.relation_group = QGroupBox(self.content)
        self.relation_group.setObjectName(u"relation_group")
        self.relation_layout = QVBoxLayout(self.relation_group)
        self.relation_layout.setObjectName(u"relation_layout")
        self.relations = QTableWidget(self.relation_group)
        if (self.relations.columnCount() < 2):
            self.relations.setColumnCount(2)
        __qtablewidgetitem = QTableWidgetItem()
        self.relations.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.relations.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        self.relations.setObjectName(u"relations")
        self.relations.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.relations.setAlternatingRowColors(True)
        self.relations.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.relations.horizontalHeader().setStretchLastSection(True)
        self.relations.verticalHeader().setVisible(False)

        self.relation_layout.addWidget(self.relations)

        self.no_relation = QLabel(self.relation_group)
        self.no_relation.setObjectName(u"no_relation")

        self.relation_layout.addWidget(self.no_relation)


        self.content_layout.addWidget(self.relation_group)

        self.file_group = QGroupBox(self.content)
        self.file_group.setObjectName(u"file_group")
        self.file_form = QFormLayout(self.file_group)
        self.file_form.setObjectName(u"file_form")
        self.mime_type_caption = QLabel(self.file_group)
        self.mime_type_caption.setObjectName(u"mime_type_caption")

        self.file_form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.mime_type_caption)

        self.type_mime = QLabel(self.file_group)
        self.type_mime.setObjectName(u"type_mime")
        self.type_mime.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.file_form.setWidget(0, QFormLayout.ItemRole.FieldRole, self.type_mime)

        self.encoding_caption = QLabel(self.file_group)
        self.encoding_caption.setObjectName(u"encoding_caption")

        self.file_form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.encoding_caption)

        self.encoding = QLabel(self.file_group)
        self.encoding.setObjectName(u"encoding")
        self.encoding.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.file_form.setWidget(1, QFormLayout.ItemRole.FieldRole, self.encoding)

        self.size_caption = QLabel(self.file_group)
        self.size_caption.setObjectName(u"size_caption")

        self.file_form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.size_caption)

        self.size = QLabel(self.file_group)
        self.size.setObjectName(u"size")
        self.size.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.file_form.setWidget(2, QFormLayout.ItemRole.FieldRole, self.size)

        self.created_caption_at = QLabel(self.file_group)
        self.created_caption_at.setObjectName(u"created_caption_at")

        self.file_form.setWidget(3, QFormLayout.ItemRole.LabelRole, self.created_caption_at)

        self.created_at = QLabel(self.file_group)
        self.created_at.setObjectName(u"created_at")
        self.created_at.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.file_form.setWidget(3, QFormLayout.ItemRole.FieldRole, self.created_at)

        self.modified_caption_at = QLabel(self.file_group)
        self.modified_caption_at.setObjectName(u"modified_caption_at")

        self.file_form.setWidget(4, QFormLayout.ItemRole.LabelRole, self.modified_caption_at)

        self.modified_at = QLabel(self.file_group)
        self.modified_at.setObjectName(u"modified_at")
        self.modified_at.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.file_form.setWidget(4, QFormLayout.ItemRole.FieldRole, self.modified_at)

        self.checked_caption_at = QLabel(self.file_group)
        self.checked_caption_at.setObjectName(u"checked_caption_at")

        self.file_form.setWidget(5, QFormLayout.ItemRole.LabelRole, self.checked_caption_at)

        self.checks_at = QLabel(self.file_group)
        self.checks_at.setObjectName(u"checks_at")
        self.checks_at.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.file_form.setWidget(5, QFormLayout.ItemRole.FieldRole, self.checks_at)


        self.content_layout.addWidget(self.file_group)

        self.edited_fields = QLabel(self.content)
        self.edited_fields.setObjectName(u"edited_fields")
        self.edited_fields.setWordWrap(True)

        self.content_layout.addWidget(self.edited_fields)

        self.content_space = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.content_layout.addItem(self.content_space)

        self.scrolling.setWidget(self.content)

        self.body.addWidget(self.scrolling)

        self.play_group = QGroupBox(SoundCard)
        self.play_group.setObjectName(u"play_group")
        self.play_layout = QVBoxLayout(self.play_group)
        self.play_layout.setObjectName(u"play_layout")
        self.plays = QTableWidget(self.play_group)
        if (self.plays.columnCount() < 7):
            self.plays.setColumnCount(7)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.plays.setHorizontalHeaderItem(0, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.plays.setHorizontalHeaderItem(1, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.plays.setHorizontalHeaderItem(2, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.plays.setHorizontalHeaderItem(3, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.plays.setHorizontalHeaderItem(4, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.plays.setHorizontalHeaderItem(5, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.plays.setHorizontalHeaderItem(6, __qtablewidgetitem8)
        self.plays.setObjectName(u"plays")
        self.plays.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.plays.setAlternatingRowColors(True)
        self.plays.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.plays.horizontalHeader().setStretchLastSection(True)
        self.plays.verticalHeader().setVisible(False)

        self.play_layout.addWidget(self.plays)


        self.body.addWidget(self.play_group)

        self.body.setStretch(0, 1)
        self.body.setStretch(1, 1)

        self.arrangement.addLayout(self.body)

        self.foot = QHBoxLayout()
        self.foot.setObjectName(u"foot")
        self.delete = QPushButton(SoundCard)
        self.delete.setObjectName(u"delete")

        self.foot.addWidget(self.delete)

        self.preview = QPushButton(SoundCard)
        self.preview.setObjectName(u"preview")

        self.foot.addWidget(self.preview)

        self.check = QPushButton(SoundCard)
        self.check.setObjectName(u"check")

        self.foot.addWidget(self.check)

        self.message = QLabel(SoundCard)
        self.message.setObjectName(u"message")
        self.message.setWordWrap(True)

        self.foot.addWidget(self.message)

        self.cancel = QPushButton(SoundCard)
        self.cancel.setObjectName(u"cancel")

        self.foot.addWidget(self.cancel)

        self.save = QPushButton(SoundCard)
        self.save.setObjectName(u"save")

        self.foot.addWidget(self.save)

        self.foot.setStretch(3, 1)

        self.arrangement.addLayout(self.foot)

        self.arrangement.setStretch(1, 1)
#if QT_CONFIG(shortcut)
        self.state_caption.setBuddy(self.state)
        self.fallback_caption.setBuddy(self.fallback)
        self.artist_caption.setBuddy(self.artist)
        self.title_caption.setBuddy(self.title)
        self.year_caption.setBuddy(self.year)
        self.album_caption.setBuddy(self.album)
        self.album_artist_caption.setBuddy(self.album_artist)
        self.category_caption.setBuddy(self.genre)
        self.composer_caption.setBuddy(self.composer)
        self.label_caption.setBuddy(self.label)
        self.track_caption.setBuddy(self.track)
        self.hiding_caption.setBuddy(self.hiding)
        self.playback_max_caption.setBuddy(self.playback_max)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(SoundCard)

        self.save.setDefault(True)


        QMetaObject.connectSlotsByName(SoundCard)
    # setupUi

    def retranslateUi(self, SoundCard):
#if QT_CONFIG(tooltip)
        self.timeline_place.setToolTip(QCoreApplication.translate("SoundCard", u"The file as the on-air output will play it, according to the settings of the form, even not yet saved", None))
#endif // QT_CONFIG(tooltip)
        self.sound_group.setTitle(QCoreApplication.translate("SoundCard", u"Sound", None))
        self.type_caption.setText(QCoreApplication.translate("SoundCard", u"Type", None))
        self.location_caption.setText(QCoreApplication.translate("SoundCard", u"Location", None))
#if QT_CONFIG(tooltip)
        self.open_folder.setToolTip(QCoreApplication.translate("SoundCard", u"Open the folder of the file in the file browser", None))
#endif // QT_CONFIG(tooltip)
        self.open_folder.setText(QCoreApplication.translate("SoundCard", u"Folder\u2026", None))
        self.duration_caption.setText(QCoreApplication.translate("SoundCard", u"Duration", None))
        self.state_caption.setText(QCoreApplication.translate("SoundCard", u"S&tate", None))
        self.stream_group.setTitle(QCoreApplication.translate("SoundCard", u"Stream", None))
        self.by_address.setText(QCoreApplication.translate("SoundCard", u"&Direct address", None))
        self.by_feed.setText(QCoreApplication.translate("SoundCard", u"&Feed", None))
        self.fallback_caption.setText(QCoreApplication.translate("SoundCard", u"&Fallback event", None))
        self.test.setText(QCoreApplication.translate("SoundCard", u"&Test the stream", None))
        self.metadata_group.setTitle(QCoreApplication.translate("SoundCard", u"Metadata", None))
        self.artist_caption.setText(QCoreApplication.translate("SoundCard", u"&Artist", None))
        self.title_caption.setText(QCoreApplication.translate("SoundCard", u"Tit&le", None))
        self.year_caption.setText(QCoreApplication.translate("SoundCard", u"Year", None))
        self.album_caption.setText(QCoreApplication.translate("SoundCard", u"Album", None))
        self.album_artist_caption.setText(QCoreApplication.translate("SoundCard", u"Album artist", None))
        self.category_caption.setText(QCoreApplication.translate("SoundCard", u"Kind", u"category"))
        self.composer_caption.setText(QCoreApplication.translate("SoundCard", u"Composer", None))
        self.label_caption.setText(QCoreApplication.translate("SoundCard", u"Label", None))
        self.track_caption.setText(QCoreApplication.translate("SoundCard", u"Track", None))
        self.other_caption.setText(QCoreApplication.translate("SoundCard", u"Others", None))
        self.broadcast_group.setTitle(QCoreApplication.translate("SoundCard", u"Broadcast", None))
        self.hiding_caption.setText(QCoreApplication.translate("SoundCard", u"Artist and title", None))
        self.has_start.setText(QCoreApplication.translate("SoundCard", u"Broadcast from", None))
        self.has_end.setText(QCoreApplication.translate("SoundCard", u"Broadcast until", None))
        self.playback_max_caption.setText(QCoreApplication.translate("SoundCard", u"Maximum of plays", None))
        self.playback_max.setSpecialValueText(QCoreApplication.translate("SoundCard", u"unlimited", None))
        self.silence_group.setTitle(QCoreApplication.translate("SoundCard", u"Transition", None))
        self.detection_silences.setText(QCoreApplication.translate("SoundCard", u"Play without the detected silences", None))
#if QT_CONFIG(tooltip)
        self.detection_silences.setToolTip(QCoreApplication.translate("SoundCard", u"Ticked, the sound is played from its detected start to its detected end, even outside a bank that removes the silences.", None))
#endif // QT_CONFIG(tooltip)
        self.has_detected_start.setText(QCoreApplication.translate("SoundCard", u"Detected start", None))
#if QT_CONFIG(tooltip)
        self.has_detected_start.setToolTip(QCoreApplication.translate("SoundCard", u"Silence at the start of the file, measured by the full audit. Unticked, no silence is detected: the start is not trimmed.", None))
#endif // QT_CONFIG(tooltip)
        self.has_detected_end.setText(QCoreApplication.translate("SoundCard", u"Detected end", None))
#if QT_CONFIG(tooltip)
        self.has_detected_end.setToolTip(QCoreApplication.translate("SoundCard", u"Silence at the end of the file, counted from its end, measured by the full audit. Unticked, no silence is detected: the end is not trimmed.", None))
#endif // QT_CONFIG(tooltip)
        self.has_start_crossfade.setText(QCoreApplication.translate("SoundCard", u"Start crossfade", None))
#if QT_CONFIG(tooltip)
        self.has_start_crossfade.setToolTip(QCoreApplication.translate("SoundCard", u"Unticked, the crossfade is not set: it comes from the bank, or from the preferences. 0 second is one.", None))
#endif // QT_CONFIG(tooltip)
        self.has_end_crossfade.setText(QCoreApplication.translate("SoundCard", u"End crossfade", None))
#if QT_CONFIG(tooltip)
        self.has_end_crossfade.setToolTip(QCoreApplication.translate("SoundCard", u"Unticked, the crossfade is not set: it comes from the bank, or from the preferences. 0 second is one.", None))
#endif // QT_CONFIG(tooltip)
        self.relation_group.setTitle(QCoreApplication.translate("SoundCard", u"Relations", None))
        ___qtablewidgetitem = self.relations.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("SoundCard", u"Kind", u"category"))
        ___qtablewidgetitem1 = self.relations.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("SoundCard", u"Name", None))
#if QT_CONFIG(tooltip)
        self.relations.setToolTip(QCoreApplication.translate("SoundCard", u"Double-click: open the card", None))
#endif // QT_CONFIG(tooltip)
        self.no_relation.setText(QCoreApplication.translate("SoundCard", u"No sequence, bank or event mentions this sound.", None))
        self.file_group.setTitle(QCoreApplication.translate("SoundCard", u"File", None))
        self.mime_type_caption.setText(QCoreApplication.translate("SoundCard", u"Type", None))
        self.encoding_caption.setText(QCoreApplication.translate("SoundCard", u"Average encoding", None))
        self.size_caption.setText(QCoreApplication.translate("SoundCard", u"Size", None))
        self.created_caption_at.setText(QCoreApplication.translate("SoundCard", u"Created on", None))
        self.modified_caption_at.setText(QCoreApplication.translate("SoundCard", u"Modified on", None))
        self.checked_caption_at.setText(QCoreApplication.translate("SoundCard", u"Last full check", None))
        self.play_group.setTitle(QCoreApplication.translate("SoundCard", u"Last plays", None))
        ___qtablewidgetitem2 = self.plays.horizontalHeaderItem(0)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("SoundCard", u"Start", None))
        ___qtablewidgetitem3 = self.plays.horizontalHeaderItem(1)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("SoundCard", u"End", None))
        ___qtablewidgetitem4 = self.plays.horizontalHeaderItem(2)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("SoundCard", u"Duration", None))
        ___qtablewidgetitem5 = self.plays.horizontalHeaderItem(3)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("SoundCard", u"Event", None))
        ___qtablewidgetitem6 = self.plays.horizontalHeaderItem(4)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("SoundCard", u"Sequence", None))
        ___qtablewidgetitem7 = self.plays.horizontalHeaderItem(5)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("SoundCard", u"Bank", None))
        ___qtablewidgetitem8 = self.plays.horizontalHeaderItem(6)
        ___qtablewidgetitem8.setText(QCoreApplication.translate("SoundCard", u"Incidents", None))
        self.delete.setText(QCoreApplication.translate("SoundCard", u"\u274c Delete\u2026", None))
#if QT_CONFIG(tooltip)
        self.delete.setToolTip(QCoreApplication.translate("SoundCard", u"Deletes the element from the database, after confirmation; no file is touched.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.preview.setToolTip(QCoreApplication.translate("SoundCard", u"Listen to the sound on the pre-listen output, never on air", None))
#endif // QT_CONFIG(tooltip)
        self.preview.setText(QCoreApplication.translate("SoundCard", u"Pre-listen\u2026", None))
#if QT_CONFIG(tooltip)
        self.check.setToolTip(QCoreApplication.translate("SoundCard", u"Decode the whole file and measure its silences, like the full audit of Machin indexer, for this sound only", None))
#endif // QT_CONFIG(tooltip)
        self.check.setText(QCoreApplication.translate("SoundCard", u"Full check", None))
        self.cancel.setText(QCoreApplication.translate("SoundCard", u"Cancel", None))
        self.save.setText(QCoreApplication.translate("SoundCard", u"Save", None))
        pass
    # retranslateUi

