# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'preview.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFormLayout,
    QHBoxLayout, QLabel, QSizePolicy, QSpacerItem,
    QToolButton, QVBoxLayout, QWidget)

class Ui_PreviewWindow(object):
    def setupUi(self, PreviewWindow):
        if not PreviewWindow.objectName():
            PreviewWindow.setObjectName(u"PreviewWindow")
        PreviewWindow.resize(520, 360)
        self.arrangement = QVBoxLayout(PreviewWindow)
        self.arrangement.setObjectName(u"arrangement")
        self.source = QLabel(PreviewWindow)
        self.source.setObjectName(u"source")
        self.source.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.source.setWordWrap(True)

        self.arrangement.addWidget(self.source)

        self.player = QHBoxLayout()
        self.player.setObjectName(u"player")
        self.playback = QToolButton(PreviewWindow)
        self.playback.setObjectName(u"playback")

        self.player.addWidget(self.playback)

        self.stop = QToolButton(PreviewWindow)
        self.stop.setObjectName(u"stop")

        self.player.addWidget(self.stop)

        self.player_space = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.player.addItem(self.player_space)

        self.time = QLabel(PreviewWindow)
        self.time.setObjectName(u"time")

        self.player.addWidget(self.time)

        self.player.setStretch(2, 1)

        self.arrangement.addLayout(self.player)

        self.timeline_area = QWidget(PreviewWindow)
        self.timeline_area.setObjectName(u"timeline_area")
        self.timeline_layout = QVBoxLayout(self.timeline_area)
        self.timeline_layout.setObjectName(u"timeline_layout")
        self.timeline_layout.setContentsMargins(0, 0, 0, 0)
        self.timeline_place = QWidget(self.timeline_area)
        self.timeline_place.setObjectName(u"timeline_place")
        self.timeline_place.setMinimumSize(QSize(0, 72))

        self.timeline_layout.addWidget(self.timeline_place)

        self.range_ = QLabel(self.timeline_area)
        self.range_.setObjectName(u"range_")
        self.range_.setWordWrap(True)

        self.timeline_layout.addWidget(self.range_)

        self.markers = QHBoxLayout()
        self.markers.setObjectName(u"markers")
        self.played_start = QToolButton(self.timeline_area)
        self.played_start.setObjectName(u"played_start")

        self.markers.addWidget(self.played_start)

        self.played_end = QToolButton(self.timeline_area)
        self.played_end.setObjectName(u"played_end")

        self.markers.addWidget(self.played_end)

        self.marker_space = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.markers.addItem(self.marker_space)

        self.as_on_air = QCheckBox(self.timeline_area)
        self.as_on_air.setObjectName(u"as_on_air")

        self.markers.addWidget(self.as_on_air)


        self.timeline_layout.addLayout(self.markers)


        self.arrangement.addWidget(self.timeline_area)

        self.vu_meter_place = QWidget(PreviewWindow)
        self.vu_meter_place.setObjectName(u"vu_meter_place")
        self.vu_meter_place.setMinimumSize(QSize(0, 36))

        self.arrangement.addWidget(self.vu_meter_place)

        self.information = QFormLayout()
        self.information.setObjectName(u"information")
        self.state_heading = QLabel(PreviewWindow)
        self.state_heading.setObjectName(u"state_heading")

        self.information.setWidget(0, QFormLayout.ItemRole.LabelRole, self.state_heading)

        self.state = QLabel(PreviewWindow)
        self.state.setObjectName(u"state")

        self.information.setWidget(0, QFormLayout.ItemRole.FieldRole, self.state)

        self.format_heading = QLabel(PreviewWindow)
        self.format_heading.setObjectName(u"format_heading")

        self.information.setWidget(1, QFormLayout.ItemRole.LabelRole, self.format_heading)

        self.format = QLabel(PreviewWindow)
        self.format.setObjectName(u"format")

        self.information.setWidget(1, QFormLayout.ItemRole.FieldRole, self.format)

        self.bitrate_heading = QLabel(PreviewWindow)
        self.bitrate_heading.setObjectName(u"bitrate_heading")

        self.information.setWidget(2, QFormLayout.ItemRole.LabelRole, self.bitrate_heading)

        self.bitrate = QLabel(PreviewWindow)
        self.bitrate.setObjectName(u"bitrate")

        self.information.setWidget(2, QFormLayout.ItemRole.FieldRole, self.bitrate)

        self.sampling_heading = QLabel(PreviewWindow)
        self.sampling_heading.setObjectName(u"sampling_heading")

        self.information.setWidget(3, QFormLayout.ItemRole.LabelRole, self.sampling_heading)

        self.sampling = QLabel(PreviewWindow)
        self.sampling.setObjectName(u"sampling")

        self.information.setWidget(3, QFormLayout.ItemRole.FieldRole, self.sampling)

        self.channel_heading = QLabel(PreviewWindow)
        self.channel_heading.setObjectName(u"channel_heading")

        self.information.setWidget(4, QFormLayout.ItemRole.LabelRole, self.channel_heading)

        self.channels = QLabel(PreviewWindow)
        self.channels.setObjectName(u"channels")

        self.information.setWidget(4, QFormLayout.ItemRole.FieldRole, self.channels)

        self.predecoded_heading = QLabel(PreviewWindow)
        self.predecoded_heading.setObjectName(u"predecoded_heading")

        self.information.setWidget(5, QFormLayout.ItemRole.LabelRole, self.predecoded_heading)

        self.predecoded = QLabel(PreviewWindow)
        self.predecoded.setObjectName(u"predecoded")

        self.information.setWidget(5, QFormLayout.ItemRole.FieldRole, self.predecoded)

        self.output_heading = QLabel(PreviewWindow)
        self.output_heading.setObjectName(u"output_heading")

        self.information.setWidget(6, QFormLayout.ItemRole.LabelRole, self.output_heading)

        self.output = QComboBox(PreviewWindow)
        self.output.setObjectName(u"output")

        self.information.setWidget(6, QFormLayout.ItemRole.FieldRole, self.output)


        self.arrangement.addLayout(self.information)

        self.message = QLabel(PreviewWindow)
        self.message.setObjectName(u"message")
        self.message.setWordWrap(True)

        self.arrangement.addWidget(self.message)

#if QT_CONFIG(shortcut)
        self.output_heading.setBuddy(self.output)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(PreviewWindow)

        QMetaObject.connectSlotsByName(PreviewWindow)
    # setupUi

    def retranslateUi(self, PreviewWindow):
        PreviewWindow.setWindowTitle(QCoreApplication.translate("PreviewWindow", u"Pr\u00e9-\u00e9coute", None))
        self.source.setText(QCoreApplication.translate("PreviewWindow", u"\u2014", None))
#if QT_CONFIG(tooltip)
        self.playback.setToolTip(QCoreApplication.translate("PreviewWindow", u"Lecture", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(accessibility)
        self.playback.setAccessibleName(QCoreApplication.translate("PreviewWindow", u"Lecture", None))
#endif // QT_CONFIG(accessibility)
        self.playback.setText(QCoreApplication.translate("PreviewWindow", u"\u23f5", None))
#if QT_CONFIG(tooltip)
        self.stop.setToolTip(QCoreApplication.translate("PreviewWindow", u"Arr\u00eat", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(accessibility)
        self.stop.setAccessibleName(QCoreApplication.translate("PreviewWindow", u"Arr\u00eat", None))
#endif // QT_CONFIG(accessibility)
        self.stop.setText(QCoreApplication.translate("PreviewWindow", u"\u23f9", None))
        self.time.setText(QCoreApplication.translate("PreviewWindow", u"\u2014", None))
#if QT_CONFIG(tooltip)
        self.range_.setToolTip(QCoreApplication.translate("PreviewWindow", u"Partie du fichier jou\u00e9e \u00e0 l'antenne, sans ses silences s'ils y sont retir\u00e9s", None))
#endif // QT_CONFIG(tooltip)
        self.range_.setText("")
#if QT_CONFIG(tooltip)
        self.played_start.setToolTip(QCoreApplication.translate("PreviewWindow", u"Lire depuis le d\u00e9but de la partie jou\u00e9e \u00e0 l'antenne", None))
#endif // QT_CONFIG(tooltip)
        self.played_start.setText(QCoreApplication.translate("PreviewWindow", u"\u21e4 D\u00e9but jou\u00e9", None))
#if QT_CONFIG(tooltip)
        self.played_end.setToolTip(QCoreApplication.translate("PreviewWindow", u"Lire depuis quelques secondes avant le fondu de sortie", None))
#endif // QT_CONFIG(tooltip)
        self.played_end.setText(QCoreApplication.translate("PreviewWindow", u"Fin jou\u00e9e \u21e5", None))
#if QT_CONFIG(tooltip)
        self.as_on_air.setToolTip(QCoreApplication.translate("PreviewWindow", u"Ne jouer que la partie jou\u00e9e \u00e0 l'antenne, avec ses fondus", None))
#endif // QT_CONFIG(tooltip)
        self.as_on_air.setText(QCoreApplication.translate("PreviewWindow", u"\u00c9couter comme \u00e0 l'antenne", None))
        self.state_heading.setText(QCoreApplication.translate("PreviewWindow", u"\u00c9tat", None))
        self.state.setText(QCoreApplication.translate("PreviewWindow", u"\u2014", None))
        self.format_heading.setText(QCoreApplication.translate("PreviewWindow", u"Format", None))
        self.format.setText(QCoreApplication.translate("PreviewWindow", u"\u2014", None))
        self.bitrate_heading.setText(QCoreApplication.translate("PreviewWindow", u"D\u00e9bit", None))
        self.bitrate.setText(QCoreApplication.translate("PreviewWindow", u"\u2014", None))
        self.sampling_heading.setText(QCoreApplication.translate("PreviewWindow", u"\u00c9chantillonnage", None))
        self.sampling.setText(QCoreApplication.translate("PreviewWindow", u"\u2014", None))
        self.channel_heading.setText(QCoreApplication.translate("PreviewWindow", u"Canaux", None))
        self.channels.setText(QCoreApplication.translate("PreviewWindow", u"\u2014", None))
        self.predecoded_heading.setText(QCoreApplication.translate("PreviewWindow", u"Pr\u00e9-d\u00e9cod\u00e9", None))
#if QT_CONFIG(tooltip)
        self.predecoded.setToolTip(QCoreApplication.translate("PreviewWindow", u"Son re\u00e7u et d\u00e9cod\u00e9 d'avance, pr\u00eat \u00e0 \u00eatre jou\u00e9", None))
#endif // QT_CONFIG(tooltip)
        self.predecoded.setText(QCoreApplication.translate("PreviewWindow", u"\u2014", None))
        self.output_heading.setText(QCoreApplication.translate("PreviewWindow", u"Sortie", None))
#if QT_CONFIG(tooltip)
        self.output.setToolTip(QCoreApplication.translate("PreviewWindow", u"P\u00e9riph\u00e9rique de pr\u00e9-\u00e9coute, jamais celui de l'antenne", None))
#endif // QT_CONFIG(tooltip)
        self.message.setText("")
    # retranslateUi

