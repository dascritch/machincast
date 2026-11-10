# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'bank_card.ui'
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
    QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QSizePolicy, QSpacerItem,
    QTimeEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget)

class Ui_BankCard(object):
    def setupUi(self, BankCard):
        if not BankCard.objectName():
            BankCard.setObjectName(u"BankCard")
        BankCard.resize(1100, 700)
        self.arrangement = QVBoxLayout(BankCard)
        self.arrangement.setObjectName(u"arrangement")
        self.form = QFormLayout()
        self.form.setObjectName(u"form")
        self.internal_name_caption = QLabel(BankCard)
        self.internal_name_caption.setObjectName(u"internal_name_caption")

        self.form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.internal_name_caption)

        self.internal_name = QLineEdit(BankCard)
        self.internal_name.setObjectName(u"internal_name")
        self.internal_name.setMaxLength(255)

        self.form.setWidget(0, QFormLayout.ItemRole.FieldRole, self.internal_name)

        self.public_name_caption = QLabel(BankCard)
        self.public_name_caption.setObjectName(u"public_name_caption")

        self.form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.public_name_caption)

        self.public_name = QLineEdit(BankCard)
        self.public_name.setObjectName(u"public_name")
        self.public_name.setMaxLength(255)

        self.form.setWidget(1, QFormLayout.ItemRole.FieldRole, self.public_name)

        self.mode_caption = QLabel(BankCard)
        self.mode_caption.setObjectName(u"mode_caption")

        self.form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.mode_caption)

        self.mode = QComboBox(BankCard)
        self.mode.setObjectName(u"mode")

        self.form.setWidget(2, QFormLayout.ItemRole.FieldRole, self.mode)

        self.hiding_caption = QLabel(BankCard)
        self.hiding_caption.setObjectName(u"hiding_caption")

        self.form.setWidget(3, QFormLayout.ItemRole.LabelRole, self.hiding_caption)

        self.hiding = QComboBox(BankCard)
        self.hiding.setObjectName(u"hiding")

        self.form.setWidget(3, QFormLayout.ItemRole.FieldRole, self.hiding)

        self.no_repeat = QCheckBox(BankCard)
        self.no_repeat.setObjectName(u"no_repeat")

        self.form.setWidget(4, QFormLayout.ItemRole.FieldRole, self.no_repeat)

        self.detection_silences = QCheckBox(BankCard)
        self.detection_silences.setObjectName(u"detection_silences")

        self.form.setWidget(5, QFormLayout.ItemRole.FieldRole, self.detection_silences)

        self.start_crossfade_caption = QLabel(BankCard)
        self.start_crossfade_caption.setObjectName(u"start_crossfade_caption")

        self.form.setWidget(6, QFormLayout.ItemRole.LabelRole, self.start_crossfade_caption)

        self.start_crossfade_layout = QHBoxLayout()
        self.start_crossfade_layout.setObjectName(u"start_crossfade_layout")
        self.start_crossfade_rule = QComboBox(BankCard)
        self.start_crossfade_rule.setObjectName(u"start_crossfade_rule")

        self.start_crossfade_layout.addWidget(self.start_crossfade_rule)

        self.start_crossfade = QDoubleSpinBox(BankCard)
        self.start_crossfade.setObjectName(u"start_crossfade")
        self.start_crossfade.setSuffix(u" s")
        self.start_crossfade.setDecimals(2)
        self.start_crossfade.setMaximum(600.000000000000000)
        self.start_crossfade.setSingleStep(0.500000000000000)

        self.start_crossfade_layout.addWidget(self.start_crossfade)

        self.start_crossfade_space = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.start_crossfade_layout.addItem(self.start_crossfade_space)

        self.start_crossfade_layout.setStretch(2, 1)

        self.form.setLayout(6, QFormLayout.ItemRole.FieldRole, self.start_crossfade_layout)

        self.end_crossfade_caption = QLabel(BankCard)
        self.end_crossfade_caption.setObjectName(u"end_crossfade_caption")

        self.form.setWidget(7, QFormLayout.ItemRole.LabelRole, self.end_crossfade_caption)

        self.end_crossfade_layout = QHBoxLayout()
        self.end_crossfade_layout.setObjectName(u"end_crossfade_layout")
        self.end_crossfade_rule = QComboBox(BankCard)
        self.end_crossfade_rule.setObjectName(u"end_crossfade_rule")

        self.end_crossfade_layout.addWidget(self.end_crossfade_rule)

        self.end_crossfade = QDoubleSpinBox(BankCard)
        self.end_crossfade.setObjectName(u"end_crossfade")
        self.end_crossfade.setSuffix(u" s")
        self.end_crossfade.setDecimals(2)
        self.end_crossfade.setMaximum(600.000000000000000)
        self.end_crossfade.setSingleStep(0.500000000000000)

        self.end_crossfade_layout.addWidget(self.end_crossfade)

        self.end_crossfade_space = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.end_crossfade_layout.addItem(self.end_crossfade_space)

        self.end_crossfade_layout.setStretch(2, 1)

        self.form.setLayout(7, QFormLayout.ItemRole.FieldRole, self.end_crossfade_layout)

        self.has_min_duration = QCheckBox(BankCard)
        self.has_min_duration.setObjectName(u"has_min_duration")

        self.form.setWidget(8, QFormLayout.ItemRole.LabelRole, self.has_min_duration)

        self.min_duration_layout = QHBoxLayout()
        self.min_duration_layout.setObjectName(u"min_duration_layout")
        self.min_duration = QTimeEdit(BankCard)
        self.min_duration.setObjectName(u"min_duration")
        self.min_duration.setEnabled(False)
        self.min_duration.setDisplayFormat(u"H:mm:ss")

        self.min_duration_layout.addWidget(self.min_duration)

        self.min_duration_space = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.min_duration_layout.addItem(self.min_duration_space)

        self.min_duration_layout.setStretch(1, 1)

        self.form.setLayout(8, QFormLayout.ItemRole.FieldRole, self.min_duration_layout)

        self.has_max_duration = QCheckBox(BankCard)
        self.has_max_duration.setObjectName(u"has_max_duration")

        self.form.setWidget(9, QFormLayout.ItemRole.LabelRole, self.has_max_duration)

        self.max_duration_layout = QHBoxLayout()
        self.max_duration_layout.setObjectName(u"max_duration_layout")
        self.max_duration = QTimeEdit(BankCard)
        self.max_duration.setObjectName(u"max_duration")
        self.max_duration.setEnabled(False)
        self.max_duration.setDisplayFormat(u"H:mm:ss")

        self.max_duration_layout.addWidget(self.max_duration)

        self.max_duration_space = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.max_duration_layout.addItem(self.max_duration_space)

        self.max_duration_layout.setStretch(1, 1)

        self.form.setLayout(9, QFormLayout.ItemRole.FieldRole, self.max_duration_layout)


        self.arrangement.addLayout(self.form)

        self.lists = QHBoxLayout()
        self.lists.setObjectName(u"lists")
        self.directory_group = QGroupBox(BankCard)
        self.directory_group.setObjectName(u"directory_group")
        self.directory_layout = QVBoxLayout(self.directory_group)
        self.directory_layout.setObjectName(u"directory_layout")
        self.directory_explanation = QLabel(self.directory_group)
        self.directory_explanation.setObjectName(u"directory_explanation")
        self.directory_explanation.setWordWrap(True)

        self.directory_layout.addWidget(self.directory_explanation)

        self.directories = QListWidget(self.directory_group)
        self.directories.setObjectName(u"directories")
        self.directories.setAlternatingRowColors(True)

        self.directory_layout.addWidget(self.directories)

        self.directory_buttons = QHBoxLayout()
        self.directory_buttons.setObjectName(u"directory_buttons")
        self.add_directory = QPushButton(self.directory_group)
        self.add_directory.setObjectName(u"add_directory")

        self.directory_buttons.addWidget(self.add_directory)

        self.remove_directory = QPushButton(self.directory_group)
        self.remove_directory.setObjectName(u"remove_directory")

        self.directory_buttons.addWidget(self.remove_directory)


        self.directory_layout.addLayout(self.directory_buttons)


        self.lists.addWidget(self.directory_group)

        self.sound_group = QGroupBox(BankCard)
        self.sound_group.setObjectName(u"sound_group")
        self.sound_layout = QVBoxLayout(self.sound_group)
        self.sound_layout.setObjectName(u"sound_layout")
        self.sound_filter = QLineEdit(self.sound_group)
        self.sound_filter.setObjectName(u"sound_filter")
        self.sound_filter.setClearButtonEnabled(True)

        self.sound_layout.addWidget(self.sound_filter)

        self.sounds = QTreeWidget(self.sound_group)
        self.sounds.setObjectName(u"sounds")
        self.sounds.setAlternatingRowColors(True)
        self.sounds.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.sounds.setRootIsDecorated(False)
        self.sounds.setUniformRowHeights(True)

        self.sound_layout.addWidget(self.sounds)

        self.sound_buttons = QHBoxLayout()
        self.sound_buttons.setObjectName(u"sound_buttons")
        self.add_sounds = QPushButton(self.sound_group)
        self.add_sounds.setObjectName(u"add_sounds")

        self.sound_buttons.addWidget(self.add_sounds)

        self.remove_sound = QPushButton(self.sound_group)
        self.remove_sound.setObjectName(u"remove_sound")

        self.sound_buttons.addWidget(self.remove_sound)

        self.sound_space = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.sound_buttons.addItem(self.sound_space)

        self.raise_ = QPushButton(self.sound_group)
        self.raise_.setObjectName(u"raise_")

        self.sound_buttons.addWidget(self.raise_)

        self.go_down = QPushButton(self.sound_group)
        self.go_down.setObjectName(u"go_down")

        self.sound_buttons.addWidget(self.go_down)


        self.sound_layout.addLayout(self.sound_buttons)


        self.lists.addWidget(self.sound_group)

        self.lists.setStretch(0, 1)
        self.lists.setStretch(1, 2)

        self.arrangement.addLayout(self.lists)

        self.foot = QHBoxLayout()
        self.foot.setObjectName(u"foot")
        self.delete = QPushButton(BankCard)
        self.delete.setObjectName(u"delete")

        self.foot.addWidget(self.delete)

        self.duplicate = QPushButton(BankCard)
        self.duplicate.setObjectName(u"duplicate")

        self.foot.addWidget(self.duplicate)

        self.message = QLabel(BankCard)
        self.message.setObjectName(u"message")
        self.message.setWordWrap(True)

        self.foot.addWidget(self.message)

        self.cancel = QPushButton(BankCard)
        self.cancel.setObjectName(u"cancel")

        self.foot.addWidget(self.cancel)

        self.save = QPushButton(BankCard)
        self.save.setObjectName(u"save")

        self.foot.addWidget(self.save)

        self.foot.setStretch(2, 1)

        self.arrangement.addLayout(self.foot)

        self.arrangement.setStretch(1, 1)
#if QT_CONFIG(shortcut)
        self.internal_name_caption.setBuddy(self.internal_name)
        self.public_name_caption.setBuddy(self.public_name)
        self.mode_caption.setBuddy(self.mode)
        self.hiding_caption.setBuddy(self.hiding)
        self.start_crossfade_caption.setBuddy(self.start_crossfade_rule)
        self.end_crossfade_caption.setBuddy(self.end_crossfade_rule)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(BankCard)

        self.save.setDefault(True)


        QMetaObject.connectSlotsByName(BankCard)
    # setupUi

    def retranslateUi(self, BankCard):
        self.internal_name_caption.setText(QCoreApplication.translate("BankCard", u"&Internal name", None))
        self.internal_name.setPlaceholderText(QCoreApplication.translate("BankCard", u"Required, and unique to this bank", None))
        self.public_name_caption.setText(QCoreApplication.translate("BankCard", u"P&ublic name", None))
        self.public_name.setPlaceholderText(QCoreApplication.translate("BankCard", u"Shown instead of the hidden artist and title; optional", None))
        self.mode_caption.setText(QCoreApplication.translate("BankCard", u"&Mode", None))
        self.hiding_caption.setText(QCoreApplication.translate("BankCard", u"&Artist and title", None))
        self.no_repeat.setText(QCoreApplication.translate("BankCard", u"Do not &repeat: the bank never plays twice in a row", None))
        self.detection_silences.setText(QCoreApplication.translate("BankCard", u"&Silence detection: the sounds are played without their detected silences", None))
#if QT_CONFIG(tooltip)
        self.detection_silences.setToolTip(QCoreApplication.translate("BankCard", u"Each sound played through the bank starts at its detected start and stops at its detected end, measured by the full audit.", None))
#endif // QT_CONFIG(tooltip)
        self.start_crossfade_caption.setText(QCoreApplication.translate("BankCard", u"Start crossfade", None))
#if QT_CONFIG(tooltip)
        self.start_crossfade_rule.setToolTip(QCoreApplication.translate("BankCard", u"The start crossfade of the sounds played through this bank: their own, the bank's for those that have none, or the bank's for all", None))
#endif // QT_CONFIG(tooltip)
        self.end_crossfade_caption.setText(QCoreApplication.translate("BankCard", u"End crossfade", None))
#if QT_CONFIG(tooltip)
        self.end_crossfade_rule.setToolTip(QCoreApplication.translate("BankCard", u"The end crossfade of the sounds played through this bank: their own, the bank's for those that have none, or the bank's for all", None))
#endif // QT_CONFIG(tooltip)
        self.has_min_duration.setText(QCoreApplication.translate("BankCard", u"Minimum duration of the sounds", None))
#if QT_CONFIG(tooltip)
        self.has_min_duration.setToolTip(QCoreApplication.translate("BankCard", u"Optional: a sound of the bank outside it is flagged, without being refused", None))
#endif // QT_CONFIG(tooltip)
        self.has_max_duration.setText(QCoreApplication.translate("BankCard", u"Maximum duration of the sounds", None))
#if QT_CONFIG(tooltip)
        self.has_max_duration.setToolTip(QCoreApplication.translate("BankCard", u"Optional: a sound of the bank outside it is flagged, without being refused", None))
#endif // QT_CONFIG(tooltip)
        self.directory_group.setTitle(QCoreApplication.translate("BankCard", u"Indexed directories", None))
        self.directory_explanation.setText(QCoreApplication.translate("BankCard", u"Machin indexer attaches to the bank the sound files of these directories and of their subdirectories.", None))
        self.add_directory.setText(QCoreApplication.translate("BankCard", u"\u2795 Add a directory\u2026", None))
        self.remove_directory.setText(QCoreApplication.translate("BankCard", u"\u2796 Remove the directory", None))
        self.sound_group.setTitle(QCoreApplication.translate("BankCard", u"Sounds", None))
#if QT_CONFIG(tooltip)
        self.sound_filter.setToolTip(QCoreApplication.translate("BankCard", u"The sounds of which a column contains this text, whatever the case and the accents", None))
#endif // QT_CONFIG(tooltip)
        self.sound_filter.setPlaceholderText(QCoreApplication.translate("BankCard", u"Filter\u2026", None))
        ___qtreewidgetitem = self.sounds.headerItem()
        ___qtreewidgetitem.setText(3, QCoreApplication.translate("BankCard", u"Location", None))
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("BankCard", u"State", None))
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("BankCard", u"Duration", None))
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("BankCard", u"Sound", None))
        self.add_sounds.setText(QCoreApplication.translate("BankCard", u"\u2795 Add sounds\u2026", None))
        self.remove_sound.setText(QCoreApplication.translate("BankCard", u"\u2796 Remove the sound", None))
        self.raise_.setText(QCoreApplication.translate("BankCard", u"Move up", None))
        self.go_down.setText(QCoreApplication.translate("BankCard", u"Move down", None))
        self.delete.setText(QCoreApplication.translate("BankCard", u"\u274c Delete\u2026", None))
#if QT_CONFIG(tooltip)
        self.delete.setToolTip(QCoreApplication.translate("BankCard", u"Deletes the element from the database, after confirmation; no file is touched.", None))
#endif // QT_CONFIG(tooltip)
        self.duplicate.setText(QCoreApplication.translate("BankCard", u"Duplicate", None))
#if QT_CONFIG(tooltip)
        self.duplicate.setToolTip(QCoreApplication.translate("BankCard", u"Opens a copy of the element in a new card; nothing is saved before \u201cSave\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.cancel.setText(QCoreApplication.translate("BankCard", u"Cancel", None))
        self.save.setText(QCoreApplication.translate("BankCard", u"Save", None))
        pass
    # retranslateUi

