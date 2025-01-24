# region Imports
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# endregion


# region Classes
class UI(QMainWindow):
    def __init__(self):
        super(UI, self).__init__()

        self.setWindowTitle("EPUB Metaclean - V4.0")
        self.setWindowIcon(QIcon("icon.png"))

        with open("styles.qss", "r") as styles:
            self.setStyleSheet(styles.read())

        self.initUI()

    def initUI(self):
        self.base_widget = QWidget()
        self.base_layout = QVBoxLayout(self)
        self.setCentralWidget(self.base_widget)

        self.top_frame = self.createWidget(QWidget, self.base_layout)
        self.middle_frame = self.createWidget(QWidget, self.base_layout)
        self.bottom_frame = self.createWidget(QWidget, self.base_layout)

        self.base_widget.setLayout(self.base_layout)
        self.showMaximized()
        self.show()

    def createWidget(self, widget_type, layout):
        widget = widget_type()
        layout.addWidget(widget)
        return widget


# endregion

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui = UI()
    sys.exit(app.exec_())
