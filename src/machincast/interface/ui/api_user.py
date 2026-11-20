# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'api_user.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QDialog,
    QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_ApiUserDialog(object):
    def setupUi(self, ApiUserDialog):
        if not ApiUserDialog.objectName():
            ApiUserDialog.setObjectName(u"ApiUserDialog")
        ApiUserDialog.resize(480, 240)
        self.arrangement = QVBoxLayout(ApiUserDialog)
        self.arrangement.setObjectName(u"arrangement")
        self.form = QFormLayout()
        self.form.setObjectName(u"form")
        self.name_label = QLabel(ApiUserDialog)
        self.name_label.setObjectName(u"name_label")

        self.form.setWidget(0, QFormLayout.ItemRole.LabelRole, self.name_label)

        self.name = QLineEdit(ApiUserDialog)
        self.name.setObjectName(u"name")
        self.name.setMaxLength(255)

        self.form.setWidget(0, QFormLayout.ItemRole.FieldRole, self.name)

        self.password_label = QLabel(ApiUserDialog)
        self.password_label.setObjectName(u"password_label")

        self.form.setWidget(1, QFormLayout.ItemRole.LabelRole, self.password_label)

        self.password = QLineEdit(ApiUserDialog)
        self.password.setObjectName(u"password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)

        self.form.setWidget(1, QFormLayout.ItemRole.FieldRole, self.password)

        self.confirmation_label = QLabel(ApiUserDialog)
        self.confirmation_label.setObjectName(u"confirmation_label")

        self.form.setWidget(2, QFormLayout.ItemRole.LabelRole, self.confirmation_label)

        self.confirmation = QLineEdit(ApiUserDialog)
        self.confirmation.setObjectName(u"confirmation")
        self.confirmation.setEchoMode(QLineEdit.EchoMode.Password)

        self.form.setWidget(2, QFormLayout.ItemRole.FieldRole, self.confirmation)

        self.role_label = QLabel(ApiUserDialog)
        self.role_label.setObjectName(u"role_label")

        self.form.setWidget(3, QFormLayout.ItemRole.LabelRole, self.role_label)

        self.role = QComboBox(ApiUserDialog)
        self.role.setObjectName(u"role")

        self.form.setWidget(3, QFormLayout.ItemRole.FieldRole, self.role)


        self.arrangement.addLayout(self.form)

        self.refusal = QLabel(ApiUserDialog)
        self.refusal.setObjectName(u"refusal")
        self.refusal.setWordWrap(True)

        self.arrangement.addWidget(self.refusal)

        self.buttons = QDialogButtonBox(ApiUserDialog)
        self.buttons.setObjectName(u"buttons")
        self.buttons.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.arrangement.addWidget(self.buttons)

#if QT_CONFIG(shortcut)
        self.name_label.setBuddy(self.name)
        self.password_label.setBuddy(self.password)
        self.confirmation_label.setBuddy(self.confirmation)
        self.role_label.setBuddy(self.role)
#endif // QT_CONFIG(shortcut)

        self.retranslateUi(ApiUserDialog)

        QMetaObject.connectSlotsByName(ApiUserDialog)
    # setupUi

    def retranslateUi(self, ApiUserDialog):
        ApiUserDialog.setWindowTitle(QCoreApplication.translate("ApiUserDialog", u"Intranet user", None))
        self.name_label.setText(QCoreApplication.translate("ApiUserDialog", u"&Name", None))
        self.name.setPlaceholderText(QCoreApplication.translate("ApiUserDialog", u"Letters without accents, digits, dot, hyphen, underscore", None))
        self.password_label.setText(QCoreApplication.translate("ApiUserDialog", u"&Password", None))
        self.confirmation_label.setText(QCoreApplication.translate("ApiUserDialog", u"&Confirmation", None))
        self.role_label.setText(QCoreApplication.translate("ApiUserDialog", u"&Role", None))
    # retranslateUi

