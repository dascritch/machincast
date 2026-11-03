# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'event_card.ui'
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
    QDateTimeEdit, QFormLayout, QGridLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QSpacerItem, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget)

class Ui_EventCard(object):
    def setupUi(self, EventCard):
        if not EventCard.objectName():
            EventCard.setObjectName(u"EventCard")
        EventCard.resize(1100, 700)
        self.arrangement = QVBoxLayout(EventCard)
        self.arrangement.setObjectName(u"arrangement")
        self.top = QHBoxLayout()
        self.top.setObjectName(u"top")
        self.form = QFormLayout()
        self.form.setObjectName(u"form")
        self.internal_name_caption = QLabel(EventCard)
        self.internal_name_caption.setObjectName(u"internal_name_caption")

        self.form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.internal_name_caption)

        self.internal_name = QLineEdit(EventCard)
        self.internal_name.setObjectName(u"internal_name")
        self.internal_name.setMaxLength(255)

        self.form.setWidget(0, QFormLayout.ItemRole.FieldRole, self.internal_name)

        self.public_name_caption = QLabel(EventCard)
        self.public_name_caption.setObjectName(u"public_name_caption")

        self.form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.public_name_caption)

        self.public_name = QLineEdit(EventCard)
        self.public_name.setObjectName(u"public_name")
        self.public_name.setMaxLength(255)

        self.form.setWidget(1, QFormLayout.ItemRole.FieldRole, self.public_name)

        self.priority_caption = QLabel(EventCard)
        self.priority_caption.setObjectName(u"priority_caption")

        self.form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.priority_caption)

        self.priority = QComboBox(EventCard)
        self.priority.setObjectName(u"priority")

        self.form.setWidget(2, QFormLayout.ItemRole.FieldRole, self.priority)

        self.hiding_caption = QLabel(EventCard)
        self.hiding_caption.setObjectName(u"hiding_caption")

        self.form.setWidget(3, QFormLayout.ItemRole.LabelRole, self.hiding_caption)

        self.hiding = QComboBox(EventCard)
        self.hiding.setObjectName(u"hiding")

        self.form.setWidget(3, QFormLayout.ItemRole.FieldRole, self.hiding)


        self.top.addLayout(self.form)

        self.grid_group = QGroupBox(EventCard)
        self.grid_group.setObjectName(u"grid_group")
        self.grid_layout = QGridLayout(self.grid_group)
        self.grid_layout.setObjectName(u"grid_layout")
        self.has_start = QCheckBox(self.grid_group)
        self.has_start.setObjectName(u"has_start")

        self.grid_layout.addWidget(self.has_start, 0, 0, 1, 1)

        self.start = QDateTimeEdit(self.grid_group)
        self.start.setObjectName(u"start")
        self.start.setEnabled(False)
        self.start.setCalendarPopup(True)

        self.grid_layout.addWidget(self.start, 0, 1, 1, 1)

        self.has_end = QCheckBox(self.grid_group)
        self.has_end.setObjectName(u"has_end")

        self.grid_layout.addWidget(self.has_end, 1, 0, 1, 1)

        self.end = QDateTimeEdit(self.grid_group)
        self.end.setObjectName(u"end")
        self.end.setEnabled(False)
        self.end.setCalendarPopup(True)

        self.grid_layout.addWidget(self.end, 1, 1, 1, 1)

        self.day_layout = QHBoxLayout()
        self.day_layout.setObjectName(u"day_layout")
        self.monday = QCheckBox(self.grid_group)
        self.monday.setObjectName(u"monday")

        self.day_layout.addWidget(self.monday)

        self.tuesday = QCheckBox(self.grid_group)
        self.tuesday.setObjectName(u"tuesday")

        self.day_layout.addWidget(self.tuesday)

        self.wednesday = QCheckBox(self.grid_group)
        self.wednesday.setObjectName(u"wednesday")

        self.day_layout.addWidget(self.wednesday)

        self.thursday = QCheckBox(self.grid_group)
        self.thursday.setObjectName(u"thursday")

        self.day_layout.addWidget(self.thursday)

        self.friday = QCheckBox(self.grid_group)
        self.friday.setObjectName(u"friday")

        self.day_layout.addWidget(self.friday)

        self.saturday = QCheckBox(self.grid_group)
        self.saturday.setObjectName(u"saturday")

        self.day_layout.addWidget(self.saturday)

        self.sunday = QCheckBox(self.grid_group)
        self.sunday.setObjectName(u"sunday")

        self.day_layout.addWidget(self.sunday)


        self.grid_layout.addLayout(self.day_layout, 2, 0, 1, 2)

        self.grid_explanation = QLabel(self.grid_group)
        self.grid_explanation.setObjectName(u"grid_explanation")
        self.grid_explanation.setWordWrap(True)

        self.grid_layout.addWidget(self.grid_explanation, 3, 0, 1, 2)


        self.top.addWidget(self.grid_group)

        self.top.setStretch(0, 1)
        self.top.setStretch(1, 1)

        self.arrangement.addLayout(self.top)

        self.lists = QHBoxLayout()
        self.lists.setObjectName(u"lists")
        self.item_group = QGroupBox(EventCard)
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

        self.add_sequences = QPushButton(self.item_group)
        self.add_sequences.setObjectName(u"add_sequences")

        self.item_buttons.addWidget(self.add_sequences)

        self.add_feeds = QPushButton(self.item_group)
        self.add_feeds.setObjectName(u"add_feeds")

        self.item_buttons.addWidget(self.add_feeds)

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


        self.arrangement.addLayout(self.lists)

        self.foot = QHBoxLayout()
        self.foot.setObjectName(u"foot")
        self.delete = QPushButton(EventCard)
        self.delete.setObjectName(u"delete")

        self.foot.addWidget(self.delete)

        self.duplicate = QPushButton(EventCard)
        self.duplicate.setObjectName(u"duplicate")

        self.foot.addWidget(self.duplicate)

        self.message = QLabel(EventCard)
        self.message.setObjectName(u"message")
        self.message.setWordWrap(True)

        self.foot.addWidget(self.message)

        self.cancel = QPushButton(EventCard)
        self.cancel.setObjectName(u"cancel")

        self.foot.addWidget(self.cancel)

        self.save = QPushButton(EventCard)
        self.save.setObjectName(u"save")

        self.foot.addWidget(self.save)

        self.foot.setStretch(2, 1)

        self.arrangement.addLayout(self.foot)

        self.arrangement.setStretch(1, 1)
#if QT_CONFIG(shortcut)
        self.internal_name_caption.setBuddy(self.internal_name)
        self.public_name_caption.setBuddy(self.public_name)
        self.priority_caption.setBuddy(self.priority)
        self.hiding_caption.setBuddy(self.hiding)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(EventCard)

        self.save.setDefault(True)


        QMetaObject.connectSlotsByName(EventCard)
    # setupUi

    def retranslateUi(self, EventCard):
        self.internal_name_caption.setText(QCoreApplication.translate("EventCard", u"&Nom interne", None))
        self.internal_name.setPlaceholderText(QCoreApplication.translate("EventCard", u"Obligatoire, et propre \u00e0 cet \u00e9v\u00e9nement", None))
        self.public_name_caption.setText(QCoreApplication.translate("EventCard", u"Nom p&ublic", None))
        self.public_name.setPlaceholderText(QCoreApplication.translate("EventCard", u"Affich\u00e9 \u00e0 la place de l'artiste et du titre masqu\u00e9s ; facultatif", None))
        self.priority_caption.setText(QCoreApplication.translate("EventCard", u"P&riorit\u00e9", None))
        self.hiding_caption.setText(QCoreApplication.translate("EventCard", u"&Artiste et titre", None))
        self.grid_group.setTitle(QCoreApplication.translate("EventCard", u"Grille : premi\u00e8re occurrence, et jours o\u00f9 elle revient", None))
        self.has_start.setText(QCoreApplication.translate("EventCard", u"&D\u00e9but", None))
        self.start.setDisplayFormat(QCoreApplication.translate("EventCard", u"dd/MM/yyyy HH:mm", None))
        self.has_end.setText(QCoreApplication.translate("EventCard", u"&Fin", None))
        self.end.setDisplayFormat(QCoreApplication.translate("EventCard", u"dd/MM/yyyy HH:mm", None))
        self.monday.setText(QCoreApplication.translate("EventCard", u"lundi", None))
        self.tuesday.setText(QCoreApplication.translate("EventCard", u"mardi", None))
        self.wednesday.setText(QCoreApplication.translate("EventCard", u"mercredi", None))
        self.thursday.setText(QCoreApplication.translate("EventCard", u"jeudi", None))
        self.friday.setText(QCoreApplication.translate("EventCard", u"vendredi", None))
        self.saturday.setText(QCoreApplication.translate("EventCard", u"samedi", None))
        self.sunday.setText(QCoreApplication.translate("EventCard", u"dimanche", None))
        self.grid_explanation.setText(QCoreApplication.translate("EventCard", u"Sans jour coch\u00e9, l'\u00e9v\u00e9nement n'a qu'une occurrence. Sans fin, une \u00e9mission ou un sp\u00e9cial dure jusqu'au bout de sa liste ; un fil musical sans d\u00e9but est permanent, et sert de fond.", None))
        self.item_group.setTitle(QCoreApplication.translate("EventCard", u"Liste de lecture, dans l'ordre de passage", None))
        ___qtreewidgetitem = self.items.headerItem()
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("EventCard", u"D\u00e9tail", None))
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("EventCard", u"\u00c9l\u00e9ment", None))
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("EventCard", u"Genre", None))
        self.add_sounds.setText(QCoreApplication.translate("EventCard", u"\u2795 Ajouter des sonores\u2026", None))
        self.add_banks.setText(QCoreApplication.translate("EventCard", u"\u2795 Ajouter des banques\u2026", None))
        self.add_sequences.setText(QCoreApplication.translate("EventCard", u"\u2795 Ajouter des s\u00e9quences\u2026", None))
#if QT_CONFIG(tooltip)
        self.add_feeds.setToolTip(QCoreApplication.translate("EventCard", u"Ajoute le stream qui suit chaque feed choisi, ou en cr\u00e9e un \u00e0 l'enregistrement", None))
#endif // QT_CONFIG(tooltip)
        self.add_feeds.setText(QCoreApplication.translate("EventCard", u"\u2795 Ajouter des feeds\u2026", None))
        self.remove_item.setText(QCoreApplication.translate("EventCard", u"\u2796 Retirer l'\u00e9l\u00e9ment", None))
        self.raise_.setText(QCoreApplication.translate("EventCard", u"Monter", None))
        self.go_down.setText(QCoreApplication.translate("EventCard", u"Descendre", None))
        self.delete.setText(QCoreApplication.translate("EventCard", u"\u274c Supprimer\u2026", None))
#if QT_CONFIG(tooltip)
        self.delete.setToolTip(QCoreApplication.translate("EventCard", u"Supprime l'\u00e9l\u00e9ment de la base, apr\u00e8s confirmation ; aucun fichier n'est touch\u00e9.", None))
#endif // QT_CONFIG(tooltip)
        self.duplicate.setText(QCoreApplication.translate("EventCard", u"Dupliquer", None))
#if QT_CONFIG(tooltip)
        self.duplicate.setToolTip(QCoreApplication.translate("EventCard", u"Ouvre une copie de l'\u00e9l\u00e9ment dans une nouvelle fiche ; rien n'est enregistr\u00e9 avant \u00ab Enregistrer \u00bb.", None))
#endif // QT_CONFIG(tooltip)
        self.cancel.setText(QCoreApplication.translate("EventCard", u"Annuler", None))
        self.save.setText(QCoreApplication.translate("EventCard", u"Enregistrer", None))
        pass
    # retranslateUi

