# region Imports
from PyQt5.QtWidgets import QApplication, QWidget

# endregion


# region Classes
class EMApp:
    def __init__(self):
        self._ConfigureApp()
        
        self.app.exec_()
    
    def _ConfigureApp(self):
        self.app = QApplication([])
        self.app.setApplicationName("EPUB Metaclean")
        self.app.setApplicationVersion("4.0")

        self.window = QWidget()
        self.window.showMaximized()
        self.window.show()


# endregion

# region Globals
ui = None
# endregion

if __name__ == "__main__":
    ui = EMApp()
