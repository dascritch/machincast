# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'sequence_card.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QFormLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPushButton,
    QSizePolicy, QSpacerItem, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget)

class Ui_SequenceCard(object):
    def setupUi(self, SequenceCard):
        if not SequenceCard.objectName():
            SequenceCard.setObjectName(u"SequenceCard")
        SequenceCard.resize(1100, 700)
        self.arrangement = QVBoxLayout(SequenceCard)
        self.arrangement.setObjectName(u"arrangement")
        self.form = QFormLayout()
        self.form.setObjectName(u"form")
        self.internal_name_caption = QLabel(SequenceCard)
        self.internal_name_caption.setObjectName(u"internal_name_caption")

        self.form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.internal_name_caption)

        self.internal_name = QLineEdit(SequenceCard)
        self.internal_name.setObjectName(u"internal_name")
        self.internal_name.setMaxLength(255)

        self.form.setWidget(0, QFormLayout.ItemRole.FieldRole, self.internal_name)

        self.public_name_caption = QLabel(SequenceCard)
        self.public_name_caption.setObjectName(u"public_name_caption")

        self.form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.public_name_caption)

        self.public_name = QLineEdit(SequenceCard)
        self.public_name.setObjectName(u"public_name")
        self.public_name.setMaxLength(255)

        self.form.setWidget(1, QFormLayout.ItemRole.FieldRole, self.public_name)

        self.hiding_caption = QLabel(SequenceCard)
        self.hiding_caption.setObjectName(u"hiding_caption")

        self.form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.hiding_caption)

        self.hiding = QComboBox(SequenceCard)
        self.hiding.setObjectName(u"hiding")

        self.form.setWidget(2, QFormLayout.ItemRole.FieldRole, self.hiding)


        self.arrangement.addLayout(self.form)

        self.lists = QHBoxLayout()
        self.lists.setObjectName(u"lists")
        self.item_group = QGroupBox(SequenceCard)
        self.item_group.setObjectName(u"item_group")
        self.item_layout = QVBoxLayout(self.item_group)
        self.item_layout.setObjectName(u"item_layout")
        self.items = QTreeWidget(self.item_group)
        self.items.setObjectName(u"items")
        self.items.setAlternatingRowColors(True)
        self.items.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.items.setRootIsDecorated(False)
        self.items.setUniformRowHeights(True)

        self.item_layout.addWidget(self.items)

        self.warning = QLabel(self.item_group)
        self.warning.setObjectName(u"warning")
        self.warning.setWordWrap(True)

        self.item_layout.addWidget(self.warning)

        self.item_buttons = QHBoxLayout()
        self.item_buttons.setObjectName(u"item_buttons")
        self.add_sounds = QPushButton(self.item_group)
        self.add_sounds.setObjectName(u"add_sounds")

        self.item_buttons.addWidget(self.add_sounds)

        self.add_banks = QPushButton(self.item_group)
        self.add_banks.setObjectName(u"add_banks")

        self.item_buttons.addWidget(self.add_banks)

        self.remove_item = QPushButton(self.item_group)
        self.remove_item.setObjectName(u"remove_item")

        self.item_buttons.addWidget(self.remove_item)

        self.item_space = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.item_buttons.addItem(self.item_space)

        self.raise_ = QPushButton(self.item_group)
        self.raise_.setObjectName(u"raise_")

        self.item_buttons.addWidget(self.raise_)

        self.go_down = QPushButton(self.item_group)
        self.go_down.setObjectName(u"go_down")

        self.item_buttons.addWidget(self.go_down)


        self.item_layout.addLayout(self.item_buttons)


        self.lists.addWidget(self.item_group)

        self.event_group = QGroupBox(SequenceCard)
        self.event_group.setObjectName(u"event_group")
        self.event_layout = QVBoxLayout(self.event_group)
        self.event_layout.setObjectName(u"event_layout")
        self.events = QListWidget(self.event_group)
        self.events.setObjectName(u"events")
        self.events.setAlternatingRowColors(True)

        self.event_layout.addWidget(self.events)

        self.event_explanation = QLabel(self.event_group)
        self.event_explanation.setObjectName(u"event_explanation")
        self.event_explanation.setWordWrap(True)

        self.event_layout.addWidget(self.event_explanation)


        self.lists.addWidget(self.event_group)

        self.lists.setStretch(0, 2)
        self.lists.setStretch(1, 1)

        self.arrangement.addLayout(self.lists)

        self.foot = QHBoxLayout()
        self.foot.setObjectName(u"foot")
        self.delete = QPushButton(SequenceCard)
        self.delete.setObjectName(u"delete")

        self.foot.addWidget(self.delete)

        self.duplicate = QPushButton(SequenceCard)
        self.duplicate.setObjectName(u"duplicate")

        self.foot.addWidget(self.duplicate)

        self.message = QLabel(SequenceCard)
        self.message.setObjectName(u"message")
        self.message.setWordWrap(True)

        self.foot.addWidget(self.message)

        self.cancel = QPushButton(SequenceCard)
        self.cancel.setObjectName(u"cancel")

        self.foot.addWidget(self.cancel)

        self.save = QPushButton(SequenceCard)
        self.save.setObjectName(u"save")

        self.foot.addWidget(self.save)

        self.foot.setStretch(2, 1)

        self.arrangement.addLayout(self.foot)

        self.arrangement.setStretch(1, 1)
#if QT_CONFIG(shortcut)
        self.internal_name_caption.setBuddy(self.internal_name)
        self.public_name_caption.setBuddy(self.public_name)
        self.hiding_caption.setBuddy(self.hiding)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(SequenceCard)

        self.save.setDefault(True)


        QMetaObject.connectSlotsByName(SequenceCard)
    # setupUi

    def retranslateUi(self, SequenceCard):
        self.internal_name_caption.setText(QCoreApplication.translate("SequenceCard", u"&Internal name", None))
        self.internal_name.setPlaceholderText(QCoreApplication.translate("SequenceCard", u"Required, and unique to this sequence", None))
        self.public_name_caption.setText(QCoreApplication.translate("SequenceCard", u"P&ublic name", None))
        self.public_name.setPlaceholderText(QCoreApplication.translate("SequenceCard", u"Shown instead of the hidden artist and title; optional", None))
        self.hiding_caption.setText(QCoreApplication.translate("SequenceCard", u"&Artist and title", None))
        self.item_group.setTitle(QCoreApplication.translate("SequenceCard", u"Elements, in the order of playing", None))
        ___qtreewidgetitem = self.items.headerItem()
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("SequenceCard", u"Detail", None))
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("SequenceCard", u"Element", None))
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("SequenceCard", u"Kind", u"category"))
        self.add_sounds.setText(QCoreApplication.translate("SequenceCard", u"\u2795 Add sounds\u2026", None))
        self.add_banks.setText(QCoreApplication.translate("SequenceCard", u"\u2795 Add banks\u2026", None))
        self.remove_item.setText(QCoreApplication.translate("SequenceCard", u"\u2796 Remove the element", None))
        self.raise_.setText(QCoreApplication.translate("SequenceCard", u"Move up", None))
        self.go_down.setText(QCoreApplication.translate("SequenceCard", u"Move down", None))
        self.event_group.setTitle(QCoreApplication.translate("SequenceCard", u"Events where it appears", None))
        self.event_explanation.setText(QCoreApplication.translate("SequenceCard", u"A sequence is placed in an event from the card of the event.", None))
        self.delete.setText(QCoreApplication.translate("SequenceCard", u"\u274c Delete\u2026", None))
#if QT_CONFIG(tooltip)
        self.delete.setToolTip(QCoreApplication.translate("SequenceCard", u"Deletes the element from the database, after confirmation; no file is touched.", None))
#endif // QT_CONFIG(tooltip)
        self.duplicate.setText(QCoreApplication.translate("SequenceCard", u"Duplicate", None))
#if QT_CONFIG(tooltip)
        self.duplicate.setToolTip(QCoreApplication.translate("SequenceCard", u"Opens a copy of the element in a new card; nothing is saved before \u201cSave\u201d.", None))
#endif // QT_CONFIG(tooltip)
        self.cancel.setText(QCoreApplication.translate("SequenceCard", u"Cancel", None))
        self.save.setText(QCoreApplication.translate("SequenceCard", u"Save", None))
        pass
    # retranslateUi

