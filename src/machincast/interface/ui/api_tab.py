# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'api_tab.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QHBoxLayout,
    QHeaderView, QLabel, QPushButton, QSizePolicy,
    QSpacerItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget)

class Ui_ApiScreen(object):
    def setupUi(self, ApiScreen):
        if not ApiScreen.objectName():
            ApiScreen.setObjectName(u"ApiScreen")
        ApiScreen.resize(1000, 600)
        self.arrangement = QVBoxLayout(ApiScreen)
        self.arrangement.setObjectName(u"arrangement")
        self.introduction = QLabel(ApiScreen)
        self.introduction.setObjectName(u"introduction")
        self.introduction.setWordWrap(True)

        self.arrangement.addWidget(self.introduction)

        self.users = QTreeWidget(ApiScreen)
        self.users.setObjectName(u"users")
        self.users.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.users.setAlternatingRowColors(True)
        self.users.setRootIsDecorated(False)
        self.users.setSortingEnabled(True)

        self.arrangement.addWidget(self.users)

        self.actions = QHBoxLayout()
        self.actions.setObjectName(u"actions")
        self.new_user = QPushButton(ApiScreen)
        self.new_user.setObjectName(u"new_user")

        self.actions.addWidget(self.new_user)

        self.role_label = QLabel(ApiScreen)
        self.role_label.setObjectName(u"role_label")

        self.actions.addWidget(self.role_label)

        self.role = QComboBox(ApiScreen)
        self.role.setObjectName(u"role")

        self.actions.addWidget(self.role)

        self.change_password = QPushButton(ApiScreen)
        self.change_password.setObjectName(u"change_password")

        self.actions.addWidget(self.change_password)

        self.disable = QPushButton(ApiScreen)
        self.disable.setObjectName(u"disable")

        self.actions.addWidget(self.disable)

        self.space = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.actions.addItem(self.space)

        self.delete = QPushButton(ApiScreen)
        self.delete.setObjectName(u"delete")

        self.actions.addWidget(self.delete)


        self.arrangement.addLayout(self.actions)

#if QT_CONFIG(shortcut)
        self.role_label.setBuddy(self.role)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(ApiScreen)

        QMetaObject.connectSlotsByName(ApiScreen)
    # setupUi

    def retranslateUi(self, ApiScreen):
        self.introduction.setText(QCoreApplication.translate("ApiScreen", u"The accounts that can connect to the intranet and to the API, once the intranet server is switched on in the service settings. A password is never kept, only its fingerprint.", None))
        ___qtreewidgetitem = self.users.headerItem()
        ___qtreewidgetitem.setText(3, QCoreApplication.translate("ApiScreen", u"Created", None))
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("ApiScreen", u"State", None))
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("ApiScreen", u"Role", None))
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("ApiScreen", u"User", None))
        self.new_user.setText(QCoreApplication.translate("ApiScreen", u"\u2795 New user\u2026", None))
        self.role_label.setText(QCoreApplication.translate("ApiScreen", u"&Role", None))
        self.change_password.setText(QCoreApplication.translate("ApiScreen", u"Change the password\u2026", None))
        self.disable.setText(QCoreApplication.translate("ApiScreen", u"Disable", None))
        self.delete.setText(QCoreApplication.translate("ApiScreen", u"\u274c Delete\u2026", None))
        pass
    # retranslateUi

