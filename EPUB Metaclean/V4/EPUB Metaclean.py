# region Imports
from PyQt5.QtWidgets import QApplication, QWidget

# endregion


# region Classes
class EMApp:
    def __init__(self):
        self.app = QApplication([])
        self.window = QWidget()

        self.app.setStyleSheet("QWidget { background-color: black; }")

        self.window.showMaximized()
        self.window.show()
        self.app.exec_()


# endregion

# region Globals
ui = None
# endregion

if __name__ == "__main__":
    ui = EMApp()
