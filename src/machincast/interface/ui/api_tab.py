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

        self.second_factor = QHBoxLayout()
        self.second_factor.setObjectName(u"second_factor")
        self.authenticator = QPushButton(ApiScreen)
        self.authenticator.setObjectName(u"authenticator")

        self.second_factor.addWidget(self.authenticator)

        self.remove_authenticator = QPushButton(ApiScreen)
        self.remove_authenticator.setObjectName(u"remove_authenticator")

        self.second_factor.addWidget(self.remove_authenticator)

        self.forget_browsers = QPushButton(ApiScreen)
        self.forget_browsers.setObjectName(u"forget_browsers")

        self.second_factor.addWidget(self.forget_browsers)

        self.second_factor_space = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.second_factor.addItem(self.second_factor_space)


        self.arrangement.addLayout(self.second_factor)

        self.sessions_label = QLabel(ApiScreen)
        self.sessions_label.setObjectName(u"sessions_label")
        self.sessions_label.setWordWrap(True)

        self.arrangement.addWidget(self.sessions_label)

        self.sessions = QTreeWidget(ApiScreen)
        self.sessions.setObjectName(u"sessions")
        self.sessions.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sessions.setAlternatingRowColors(True)
        self.sessions.setRootIsDecorated(False)

        self.arrangement.addWidget(self.sessions)

        self.session_actions = QHBoxLayout()
        self.session_actions.setObjectName(u"session_actions")
        self.new_session = QPushButton(ApiScreen)
        self.new_session.setObjectName(u"new_session")

        self.session_actions.addWidget(self.new_session)

        self.invalidate_session = QPushButton(ApiScreen)
        self.invalidate_session.setObjectName(u"invalidate_session")

        self.session_actions.addWidget(self.invalidate_session)

        self.session_space = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.session_actions.addItem(self.session_space)


        self.arrangement.addLayout(self.session_actions)

#if QT_CONFIG(shortcut)
        self.role_label.setBuddy(self.role)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(ApiScreen)

        QMetaObject.connectSlotsByName(ApiScreen)
    # setupUi

    def retranslateUi(self, ApiScreen):
        self.introduction.setText(QCoreApplication.translate("ApiScreen", u"The accounts that can connect to the intranet and to the API, once the intranet server is switched on in the service settings. A password is never kept, only its fingerprint.", None))
        ___qtreewidgetitem = self.users.headerItem()
        ___qtreewidgetitem.setText(5, QCoreApplication.translate("ApiScreen", u"Known browsers", None))
        ___qtreewidgetitem.setText(4, QCoreApplication.translate("ApiScreen", u"Authentication app", None))
        ___qtreewidgetitem.setText(3, QCoreApplication.translate("ApiScreen", u"Created", None))
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("ApiScreen", u"State", None))
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("ApiScreen", u"Role", None))
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("ApiScreen", u"User", None))
        self.new_user.setText(QCoreApplication.translate("ApiScreen", u"\u2795 New user\u2026", None))
        self.role_label.setText(QCoreApplication.translate("ApiScreen", u"&Role", None))
        self.change_password.setText(QCoreApplication.translate("ApiScreen", u"Change the password\u2026", None))
        self.disable.setText(QCoreApplication.translate("ApiScreen", u"Disable", None))
        self.delete.setText(QCoreApplication.translate("ApiScreen", u"\u274c Delete\u2026", None))
#if QT_CONFIG(tooltip)
        self.authenticator.setToolTip(QCoreApplication.translate("ApiScreen", u"A new key for the authentication app of the account, the second factor of the intranet", None))
#endif // QT_CONFIG(tooltip)
        self.authenticator.setText(QCoreApplication.translate("ApiScreen", u"Authentication app\u2026", None))
        self.remove_authenticator.setText(QCoreApplication.translate("ApiScreen", u"Remove the authentication app", None))
#if QT_CONFIG(tooltip)
        self.forget_browsers.setToolTip(QCoreApplication.translate("ApiScreen", u"Its next connection, from any browser, goes through the first connection again", None))
#endif // QT_CONFIG(tooltip)
        self.forget_browsers.setText(QCoreApplication.translate("ApiScreen", u"Forget its browsers", None))
        self.sessions_label.setText(QCoreApplication.translate("ApiScreen", u"Sessions of the chosen user: waiting for validation at the desk, valid until their limit, or invalid.", None))
        ___qtreewidgetitem1 = self.sessions.headerItem()
        ___qtreewidgetitem1.setText(5, QCoreApplication.translate("ApiScreen", u"Browser", None))
        ___qtreewidgetitem1.setText(4, QCoreApplication.translate("ApiScreen", u"Address", None))
        ___qtreewidgetitem1.setText(3, QCoreApplication.translate("ApiScreen", u"Limit", None))
        ___qtreewidgetitem1.setText(2, QCoreApplication.translate("ApiScreen", u"Opened", None))
        ___qtreewidgetitem1.setText(1, QCoreApplication.translate("ApiScreen", u"Origin", None))
        ___qtreewidgetitem1.setText(0, QCoreApplication.translate("ApiScreen", u"State", None))
        self.new_session.setText(QCoreApplication.translate("ApiScreen", u"\u2795 New API session\u2026", None))
        self.invalidate_session.setText(QCoreApplication.translate("ApiScreen", u"Invalidate the session", None))
        pass
    # retranslateUi

