# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'preferences.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QSpacerItem, QSpinBox, QTabWidget,
    QVBoxLayout, QWidget)

class Ui_PreferencesWindow(object):
    def setupUi(self, PreferencesWindow):
        if not PreferencesWindow.objectName():
            PreferencesWindow.setObjectName(u"PreferencesWindow")
        self.arrangement = QVBoxLayout(PreferencesWindow)
        self.arrangement.setObjectName(u"arrangement")
        self.pages = QTabWidget(PreferencesWindow)
        self.pages.setObjectName(u"pages")
        self.page_crossfades = QWidget()
        self.page_crossfades.setObjectName(u"page_crossfades")
        self.crossfades_layout = QVBoxLayout(self.page_crossfades)
        self.crossfades_layout.setObjectName(u"crossfades_layout")
        self.crossfades_group = QGroupBox(self.page_crossfades)
        self.crossfades_group.setObjectName(u"crossfades_group")
        self.crossfades_form = QFormLayout(self.crossfades_group)
        self.crossfades_form.setObjectName(u"crossfades_form")
        self.granularity_caption = QLabel(self.crossfades_group)
        self.granularity_caption.setObjectName(u"granularity_caption")

        self.crossfades_form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.granularity_caption)

        self.granularity = QComboBox(self.crossfades_group)
        self.granularity.setObjectName(u"granularity")

        self.crossfades_form.setWidget(0, QFormLayout.ItemRole.FieldRole, self.granularity)

        self.maximum_caption = QLabel(self.crossfades_group)
        self.maximum_caption.setObjectName(u"maximum_caption")

        self.crossfades_form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.maximum_caption)

        self.maximum = QDoubleSpinBox(self.crossfades_group)
        self.maximum.setObjectName(u"maximum")
        self.maximum.setSuffix(u" s")
        self.maximum.setMaximum(600.000000000000000)

        self.crossfades_form.setWidget(1, QFormLayout.ItemRole.FieldRole, self.maximum)

        self.has_start = QCheckBox(self.crossfades_group)
        self.has_start.setObjectName(u"has_start")

        self.crossfades_form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.has_start)

        self.start = QDoubleSpinBox(self.crossfades_group)
        self.start.setObjectName(u"start")
        self.start.setEnabled(False)
        self.start.setSuffix(u" s")

        self.crossfades_form.setWidget(2, QFormLayout.ItemRole.FieldRole, self.start)

        self.has_end = QCheckBox(self.crossfades_group)
        self.has_end.setObjectName(u"has_end")

        self.crossfades_form.setWidget(3, QFormLayout.ItemRole.LabelRole, self.has_end)

        self.end = QDoubleSpinBox(self.crossfades_group)
        self.end.setObjectName(u"end")
        self.end.setEnabled(False)
        self.end.setSuffix(u" s")

        self.crossfades_form.setWidget(3, QFormLayout.ItemRole.FieldRole, self.end)


        self.crossfades_layout.addWidget(self.crossfades_group)

        self.position_group = QGroupBox(self.page_crossfades)
        self.position_group.setObjectName(u"position_group")
        self.position_form = QFormLayout(self.position_group)
        self.position_form.setObjectName(u"position_form")
        self.entry_position_caption = QLabel(self.position_group)
        self.entry_position_caption.setObjectName(u"entry_position_caption")

        self.position_form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.entry_position_caption)

        self.entry_position = QComboBox(self.position_group)
        self.entry_position.setObjectName(u"entry_position")

        self.position_form.setWidget(0, QFormLayout.ItemRole.FieldRole, self.entry_position)

        self.output_position_caption = QLabel(self.position_group)
        self.output_position_caption.setObjectName(u"output_position_caption")

        self.position_form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.output_position_caption)

        self.output_position = QComboBox(self.position_group)
        self.output_position.setObjectName(u"output_position")

        self.position_form.setWidget(1, QFormLayout.ItemRole.FieldRole, self.output_position)

        self.place_demonstration = QWidget(self.position_group)
        self.place_demonstration.setObjectName(u"place_demonstration")
        self.place_demonstration.setMinimumSize(QSize(360, 72))

        self.position_form.setWidget(2, QFormLayout.ItemRole.SpanningRole, self.place_demonstration)

        self.demonstration_legend = QLabel(self.position_group)
        self.demonstration_legend.setObjectName(u"demonstration_legend")
        self.demonstration_legend.setWordWrap(True)

        self.position_form.setWidget(3, QFormLayout.ItemRole.SpanningRole, self.demonstration_legend)


        self.crossfades_layout.addWidget(self.position_group)

        self.silence_group = QGroupBox(self.page_crossfades)
        self.silence_group.setObjectName(u"silence_group")
        self.silence_form = QFormLayout(self.silence_group)
        self.silence_form.setObjectName(u"silence_form")
        self.silence_threshold_caption = QLabel(self.silence_group)
        self.silence_threshold_caption.setObjectName(u"silence_threshold_caption")

        self.silence_form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.silence_threshold_caption)

        self.silence_threshold = QDoubleSpinBox(self.silence_group)
        self.silence_threshold.setObjectName(u"silence_threshold")
        self.silence_threshold.setSuffix(u" dB")
        self.silence_threshold.setDecimals(1)
        self.silence_threshold.setMinimum(-100.000000000000000)
        self.silence_threshold.setMaximum(-0.100000000000000)
        self.silence_threshold.setSingleStep(1.000000000000000)
        self.silence_threshold.setValue(-40.000000000000000)

        self.silence_form.setWidget(0, QFormLayout.ItemRole.FieldRole, self.silence_threshold)


        self.crossfades_layout.addWidget(self.silence_group)

        self.silence_explanation = QLabel(self.page_crossfades)
        self.silence_explanation.setObjectName(u"silence_explanation")
        self.silence_explanation.setWordWrap(True)

        self.crossfades_layout.addWidget(self.silence_explanation)

        self.explanation = QLabel(self.page_crossfades)
        self.explanation.setObjectName(u"explanation")
        self.explanation.setWordWrap(True)

        self.crossfades_layout.addWidget(self.explanation)

        self.pages.addTab(self.page_crossfades, "")
        self.page_interface = QWidget()
        self.page_interface.setObjectName(u"page_interface")
        self.interface_layout = QVBoxLayout(self.page_interface)
        self.interface_layout.setObjectName(u"interface_layout")
        self.home_group = QGroupBox(self.page_interface)
        self.home_group.setObjectName(u"home_group")
        self.home_layout = QVBoxLayout(self.home_group)
        self.home_layout.setObjectName(u"home_layout")
        self.clipping = QCheckBox(self.home_group)
        self.clipping.setObjectName(u"clipping")

        self.home_layout.addWidget(self.clipping)

        self.suggestions = QCheckBox(self.home_group)
        self.suggestions.setObjectName(u"suggestions")

        self.home_layout.addWidget(self.suggestions)


        self.interface_layout.addWidget(self.home_group)

        self.icon_group = QGroupBox(self.page_interface)
        self.icon_group.setObjectName(u"icon_group")
        self.icon_layout = QVBoxLayout(self.icon_group)
        self.icon_layout.setObjectName(u"icon_layout")
        self.icon_line = QHBoxLayout()
        self.icon_line.setObjectName(u"icon_line")
        self.preview_icon = QLabel(self.icon_group)
        self.preview_icon.setObjectName(u"preview_icon")
        self.preview_icon.setMinimumSize(QSize(48, 48))
        self.preview_icon.setMaximumSize(QSize(48, 48))

        self.icon_line.addWidget(self.preview_icon)

        self.path_icon = QLabel(self.icon_group)
        self.path_icon.setObjectName(u"path_icon")
        self.path_icon.setWordWrap(True)
        self.path_icon.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.icon_line.addWidget(self.path_icon)

        self.choose_icon = QPushButton(self.icon_group)
        self.choose_icon.setObjectName(u"choose_icon")

        self.icon_line.addWidget(self.choose_icon)

        self.default_icon = QPushButton(self.icon_group)
        self.default_icon.setObjectName(u"default_icon")

        self.icon_line.addWidget(self.default_icon)

        self.icon_line.setStretch(1, 1)

        self.icon_layout.addLayout(self.icon_line)

        self.error_icon = QLabel(self.icon_group)
        self.error_icon.setObjectName(u"error_icon")
        self.error_icon.setWordWrap(True)

        self.icon_layout.addWidget(self.error_icon)


        self.interface_layout.addWidget(self.icon_group)

        self.pages.addTab(self.page_interface, "")
        self.page_audio = QWidget()
        self.page_audio.setObjectName(u"page_audio")
        self.audio_layout = QVBoxLayout(self.page_audio)
        self.audio_layout.setObjectName(u"audio_layout")
        self.device_group = QGroupBox(self.page_audio)
        self.device_group.setObjectName(u"device_group")
        self.device_layout = QVBoxLayout(self.device_group)
        self.device_layout.setObjectName(u"device_layout")

        self.audio_layout.addWidget(self.device_group)

        self.audio_explanation = QLabel(self.page_audio)
        self.audio_explanation.setObjectName(u"audio_explanation")
        self.audio_explanation.setWordWrap(True)

        self.audio_layout.addWidget(self.audio_explanation)

        self.dead_air_group = QGroupBox(self.page_audio)
        self.dead_air_group.setObjectName(u"dead_air_group")
        self.dead_air_form = QFormLayout(self.dead_air_group)
        self.dead_air_form.setObjectName(u"dead_air_form")
        self.dead_air_fallback = QCheckBox(self.dead_air_group)
        self.dead_air_fallback.setObjectName(u"dead_air_fallback")

        self.dead_air_form.setWidget(0, QFormLayout.ItemRole.SpanningRole, self.dead_air_fallback)

        self.dead_air_duration_caption = QLabel(self.dead_air_group)
        self.dead_air_duration_caption.setObjectName(u"dead_air_duration_caption")

        self.dead_air_form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.dead_air_duration_caption)

        self.dead_air_duration = QDoubleSpinBox(self.dead_air_group)
        self.dead_air_duration.setObjectName(u"dead_air_duration")
        self.dead_air_duration.setSuffix(u" s")
        self.dead_air_duration.setDecimals(1)
        self.dead_air_duration.setMinimum(1.000000000000000)
        self.dead_air_duration.setMaximum(300.000000000000000)
        self.dead_air_duration.setSingleStep(1.000000000000000)
        self.dead_air_duration.setValue(10.000000000000000)

        self.dead_air_form.setWidget(1, QFormLayout.ItemRole.FieldRole, self.dead_air_duration)

        self.dead_air_threshold_caption = QLabel(self.dead_air_group)
        self.dead_air_threshold_caption.setObjectName(u"dead_air_threshold_caption")

        self.dead_air_form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.dead_air_threshold_caption)

        self.dead_air_threshold = QDoubleSpinBox(self.dead_air_group)
        self.dead_air_threshold.setObjectName(u"dead_air_threshold")
        self.dead_air_threshold.setSuffix(u" dB")
        self.dead_air_threshold.setDecimals(1)
        self.dead_air_threshold.setMinimum(-100.000000000000000)
        self.dead_air_threshold.setMaximum(-0.100000000000000)
        self.dead_air_threshold.setSingleStep(1.000000000000000)
        self.dead_air_threshold.setValue(-90.000000000000000)

        self.dead_air_form.setWidget(2, QFormLayout.ItemRole.FieldRole, self.dead_air_threshold)


        self.audio_layout.addWidget(self.dead_air_group)

        self.dead_air_explanation = QLabel(self.page_audio)
        self.dead_air_explanation.setObjectName(u"dead_air_explanation")
        self.dead_air_explanation.setWordWrap(True)

        self.audio_layout.addWidget(self.dead_air_explanation)

        self.audio_space = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.audio_layout.addItem(self.audio_space)

        self.pages.addTab(self.page_audio, "")
        self.database_page = QWidget()
        self.database_page.setObjectName(u"database_page")
        self.database_layout = QVBoxLayout(self.database_page)
        self.database_layout.setObjectName(u"database_layout")
        self.database_form = QFormLayout()
        self.database_form.setObjectName(u"database_form")
        self.retention_caption = QLabel(self.database_page)
        self.retention_caption.setObjectName(u"retention_caption")

        self.database_form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.retention_caption)

        self.retention = QSpinBox(self.database_page)
        self.retention.setObjectName(u"retention")
        self.retention.setMinimum(1)
        self.retention.setMaximum(3650)
        self.retention.setValue(60)

        self.database_form.setWidget(0, QFormLayout.ItemRole.FieldRole, self.retention)


        self.database_layout.addLayout(self.database_form)

        self.retention_explanation = QLabel(self.database_page)
        self.retention_explanation.setObjectName(u"retention_explanation")
        self.retention_explanation.setWordWrap(True)

        self.database_layout.addWidget(self.retention_explanation)

        self.database_space = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.database_layout.addItem(self.database_space)

        self.pages.addTab(self.database_page, "")

        self.arrangement.addWidget(self.pages)

        self.buttons = QDialogButtonBox(PreferencesWindow)
        self.buttons.setObjectName(u"buttons")
        self.buttons.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.arrangement.addWidget(self.buttons)

#if QT_CONFIG(shortcut)
        self.granularity_caption.setBuddy(self.granularity)
        self.maximum_caption.setBuddy(self.maximum)
        self.entry_position_caption.setBuddy(self.entry_position)
        self.output_position_caption.setBuddy(self.output_position)
        self.silence_threshold_caption.setBuddy(self.silence_threshold)
        self.dead_air_duration_caption.setBuddy(self.dead_air_duration)
        self.dead_air_threshold_caption.setBuddy(self.dead_air_threshold)
        self.retention_caption.setBuddy(self.retention)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(PreferencesWindow)

        QMetaObject.connectSlotsByName(PreferencesWindow)
    # setupUi

    def retranslateUi(self, PreferencesWindow):
        PreferencesWindow.setWindowTitle(QCoreApplication.translate("PreferencesWindow", u"Preferences", None))
        self.crossfades_group.setTitle(QCoreApplication.translate("PreferencesWindow", u"Durations", None))
        self.granularity_caption.setText(QCoreApplication.translate("PreferencesWindow", u"&Granularity", None))
#if QT_CONFIG(tooltip)
        self.granularity.setToolTip(QCoreApplication.translate("PreferencesWindow", u"The step of all the crossfades of the interface", None))
#endif // QT_CONFIG(tooltip)
        self.maximum_caption.setText(QCoreApplication.translate("PreferencesWindow", u"&Maximum duration", None))
#if QT_CONFIG(tooltip)
        self.maximum.setToolTip(QCoreApplication.translate("PreferencesWindow", u"The longest crossfade that the cards offer", None))
#endif // QT_CONFIG(tooltip)
        self.has_start.setText(QCoreApplication.translate("PreferencesWindow", u"Default &start", None))
#if QT_CONFIG(tooltip)
        self.has_start.setToolTip(QCoreApplication.translate("PreferencesWindow", u"The start crossfade of a sound that has none set, and that its bank does not set", None))
#endif // QT_CONFIG(tooltip)
        self.has_end.setText(QCoreApplication.translate("PreferencesWindow", u"Default &end", None))
#if QT_CONFIG(tooltip)
        self.has_end.setToolTip(QCoreApplication.translate("PreferencesWindow", u"The end crossfade of a sound that has none set, and that its bank does not set", None))
#endif // QT_CONFIG(tooltip)
        self.position_group.setTitle(QCoreApplication.translate("PreferencesWindow", u"Position of the fades, for a sound played without its silences", None))
#if QT_CONFIG(tooltip)
        self.position_group.setToolTip(QCoreApplication.translate("PreferencesWindow", u"Where the fades fall compared to the detected start and end of a sound played without its silences, whatever its bank", None))
#endif // QT_CONFIG(tooltip)
        self.entry_position_caption.setText(QCoreApplication.translate("PreferencesWindow", u"The fade-in, at the detected start", None))
        self.output_position_caption.setText(QCoreApplication.translate("PreferencesWindow", u"The fade-out, at the detected end", None))
#if QT_CONFIG(tooltip)
        self.place_demonstration.setToolTip(QCoreApplication.translate("PreferencesWindow", u"Demonstration: a sound of 30 s, with silences of 3 s at the start and 4 s at the end, removed on air, with the default crossfades entered", None))
#endif // QT_CONFIG(tooltip)
        self.demonstration_legend.setText("")
        self.silence_group.setTitle(QCoreApplication.translate("PreferencesWindow", u"Silence detection", None))
        self.silence_threshold_caption.setText(QCoreApplication.translate("PreferencesWindow", u"&Silence threshold", None))
#if QT_CONFIG(tooltip)
        self.silence_threshold.setToolTip(QCoreApplication.translate("PreferencesWindow", u"Peak level below which the start and the end of a sound are a silence; 0 dB is the full scale", None))
#endif // QT_CONFIG(tooltip)
        self.silence_explanation.setText(QCoreApplication.translate("PreferencesWindow", u"The full audit measures the silences at the start and at the end of each file at this threshold; a new threshold applies to the next audits. A bank, or a sound, chooses to be played without its silences.", None))
        self.explanation.setText(QCoreApplication.translate("PreferencesWindow", u"The cards opened afterwards follow these settings. Machin player takes the default durations at its next start.", None))
        self.pages.setTabText(self.pages.indexOf(self.page_crossfades), QCoreApplication.translate("PreferencesWindow", u"Crossfades", None))
        self.home_group.setTitle(QCoreApplication.translate("PreferencesWindow", u"Home", None))
        self.clipping.setText(QCoreApplication.translate("PreferencesWindow", u"Show the clipping light of the On air tab", None))
#if QT_CONFIG(tooltip)
        self.clipping.setToolTip(QCoreApplication.translate("PreferencesWindow", u"The \u201cClipping\u201d light of the On air column, above the VU meter; the VU meter always shows the peaks.", None))
#endif // QT_CONFIG(tooltip)
        self.suggestions.setText(QCoreApplication.translate("PreferencesWindow", u"Offer at launch what is missing to start", None))
#if QT_CONFIG(tooltip)
        self.suggestions.setToolTip(QCoreApplication.translate("PreferencesWindow", u"Background programming, basic banks and on-air device, in a window when the interface is launched.", None))
#endif // QT_CONFIG(tooltip)
        self.icon_group.setTitle(QCoreApplication.translate("PreferencesWindow", u"Application icon", None))
#if QT_CONFIG(tooltip)
        self.icon_group.setToolTip(QCoreApplication.translate("PreferencesWindow", u"The icon of the MachinCast windows, of its shortcut in the applications menu and on the desktop, and of the taskbar.", None))
#endif // QT_CONFIG(tooltip)
        self.choose_icon.setText(QCoreApplication.translate("PreferencesWindow", u"&Choose an image\u2026", None))
#if QT_CONFIG(tooltip)
        self.choose_icon.setToolTip(QCoreApplication.translate("PreferencesWindow", u"An SVG, PNG or JPEG image, preferably square", None))
#endif // QT_CONFIG(tooltip)
        self.default_icon.setText(QCoreApplication.translate("PreferencesWindow", u"MachinCast icon", None))
#if QT_CONFIG(tooltip)
        self.default_icon.setToolTip(QCoreApplication.translate("PreferencesWindow", u"Go back to the MachinCast icon", None))
#endif // QT_CONFIG(tooltip)
        self.pages.setTabText(self.pages.indexOf(self.page_interface), QCoreApplication.translate("PreferencesWindow", u"Interface", None))
        self.device_group.setTitle(QCoreApplication.translate("PreferencesWindow", u"Sound cards", None))
        self.audio_explanation.setText(QCoreApplication.translate("PreferencesWindow", u"Machin player takes the output type and the on-air card at its next start; without an on-air card, it refuses to broadcast. The pre-listen can never use the on-air card: each one is greyed out in the other choice. \u201cTest\u201d plays 2 seconds of test sound on the card of its line.", None))
        self.dead_air_group.setTitle(QCoreApplication.translate("PreferencesWindow", u"Dead air in a sound, on air", None))
#if QT_CONFIG(tooltip)
        self.dead_air_fallback.setToolTip(QCoreApplication.translate("PreferencesWindow", u"Ticked, a dead air moves on to the next sound, or to the fallback of a stream; otherwise, it is only noted in the log", None))
#endif // QT_CONFIG(tooltip)
        self.dead_air_fallback.setText(QCoreApplication.translate("PreferencesWindow", u"Move on to the next sound, or to the fallback of a s&tream", None))
        self.dead_air_duration_caption.setText(QCoreApplication.translate("PreferencesWindow", u"D&uration of a dead air", None))
#if QT_CONFIG(tooltip)
        self.dead_air_duration.setToolTip(QCoreApplication.translate("PreferencesWindow", u"Duration for which a playing sound must stay below the dead air level", None))
#endif // QT_CONFIG(tooltip)
        self.dead_air_threshold_caption.setText(QCoreApplication.translate("PreferencesWindow", u"Dead air &level", None))
#if QT_CONFIG(tooltip)
        self.dead_air_threshold.setToolTip(QCoreApplication.translate("PreferencesWindow", u"Peak level below which a playing sound no longer gives any sound; 0 dB is the full scale", None))
#endif // QT_CONFIG(tooltip)
        self.dead_air_explanation.setText(QCoreApplication.translate("PreferencesWindow", u"A sound that stays this duration below this level, while it plays, is noted in the log. Ticked, a file at once leaves the on-air output to the next sound, and a stream to its fallback, until its sound comes back. It is not a silence, at the start or at the end of a file. Machin player takes these settings at its next start.", None))
        self.pages.setTabText(self.pages.indexOf(self.page_audio), QCoreApplication.translate("PreferencesWindow", u"Audio", None))
        self.retention_caption.setText(QCoreApplication.translate("PreferencesWindow", u"Expiry &duration", None))
        self.retention.setSuffix(QCoreApplication.translate("PreferencesWindow", u" days", None))
        self.retention_explanation.setText(QCoreApplication.translate("PreferencesWindow", u"Machin purge erases from the database the plays of the airplay and the lines of the log older than this duration, and the sounds, banks, sequences and events deleted for longer. It never touches the sound files.", None))
        self.pages.setTabText(self.pages.indexOf(self.database_page), QCoreApplication.translate("PreferencesWindow", u"Database", None))
    # retranslateUi

