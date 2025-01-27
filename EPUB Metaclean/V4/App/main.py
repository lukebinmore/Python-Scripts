# region Imports
import sys
import os
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import *


# endregion


# region Packing Functions
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# endregion


# region Classes
class Container:
    PREFERRED = QSizePolicy.Preferred

    def __init__(
        self,
        parent=None,
        name=None,
        verticle=True,
        hor_policy=None,
        ver_policy=None,
    ):
        self.W = QFrame(parent.W) if parent else QFrame()
        self.L = QVBoxLayout(self.W) if verticle else QHBoxLayout(self.W)
        self.W.setLayout(self.L)
        self.W.setObjectName(name)

        hor_policy = hor_policy if hor_policy is not None else self.PREFERRED
        ver_policy = ver_policy if ver_policy is not None else self.PREFERRED
        self.W.setSizePolicy(hor_policy, ver_policy)

        self.setSpacing(3)
        self.setMargins(0, 0, 0, 0)

        parent.L.addWidget(self.W) if parent else None

    def add(self, widget, *args, **kwargs):
        self.L.addWidget(widget, *args, **kwargs)

    def insert(self, widget, *args, **kwargs):
        self.L.insertWidget(widget, *args, **kwargs)

    def setSpacing(self, spacing=0):
        self.L.setSpacing(spacing)

    def setMargins(self, left=None, top=None, right=None, bottom=None):
        curr_left, curr_top, curr_right, curr_bottom = (
            self.L.getContentsMargins()
        )

        left = left if left is not None else curr_left
        top = top if top is not None else curr_top
        right = right if right is not None else curr_right
        bottom = bottom if bottom is not None else curr_bottom

        self.L.setContentsMargins(left, top, right, bottom)

    def hide(self):
        self.W.setVisible(False)

    def show(self):
        self.W.setVisible(True)


class PushButton(QPushButton):
    PREFERRED = QSizePolicy.Policy.Preferred

    def __init__(
        self,
        parent,
        name=None,
        text=None,
        hor_policy=None,
        ver_policy=None,
        warn=False,
    ):
        super(PushButton, self).__init__(parent.W)
        self.setObjectName(name)
        self.setProperty("theme", "warn") if warn else None
        self.setText(text)

        hor_policy = hor_policy if hor_policy is not None else self.PREFERRED
        ver_policy = ver_policy if ver_policy is not None else self.PREFERRED
        self.setSizePolicy(hor_policy, ver_policy)

        parent.add(self)


class Label(QLabel):
    PREFERRED = QSizePolicy.Policy.Preferred

    def __init__(
        self, parent, name=None, text=None, hor_policy=None, ver_policy=None
    ):
        super(Label, self).__init__(parent.W)
        self.setObjectName(name)
        self.setText(text)

        hor_policy = hor_policy if hor_policy is not None else self.PREFERRED
        ver_policy = ver_policy if ver_policy is not None else self.PREFERRED
        self.setSizePolicy(hor_policy, ver_policy)

        parent.add(self)


class ProgressBar(QProgressBar):
    PREFERRED = QSizePolicy.Policy.Preferred

    def __init__(self, parent, name=None, hor_policy=None, ver_policy=None):
        super(ProgressBar, self).__init__(parent.W)
        self.setObjectName(name)
        self.setFormat("")

        hor_policy = hor_policy if hor_policy is not None else self.PREFERRED
        ver_policy = ver_policy if ver_policy is not None else self.PREFERRED
        self.setSizePolicy(hor_policy, ver_policy)

        parent.add(self)


class WebEngineView(QWebEngineView):
    PREFERRED = QSizePolicy.Policy.Preferred

    def __init__(self, parent, name=None, hor_policy=None, ver_policy=None):
        super(WebEngineView, self).__init__(parent.W)
        self.setObjectName(name)

        hor_policy = hor_policy if hor_policy is not None else self.PREFERRED
        ver_policy = ver_policy if ver_policy is not None else self.PREFERRED
        self.setSizePolicy(hor_policy, ver_policy)

        parent.add(self)


class UI(QMainWindow):
    DEFAULT_MARGIN = 3, 3, 3, 3
    EXPANDING = QSizePolicy.Expanding
    MINIMUM = QSizePolicy.Minimum
    STYLE_VARIABLES = {
        "text_size": 1,
        "header_size": 1,
        "primary_color": "#4CBB17",
        "primary_dark_color": "#2e720e",
        "secondary_color": "",
        "secondary_dark_color": "",
        "button_color": "#ffffff",
        "button_color_alt": "#ffffff",
        "border_color": "#ffffff",
        "border_color_alt": "#ffffff",
        "bg_color": "#323232",
        "bg_alt_color": "#595959",
        "hover_color": "#000000",
        "hover_bgcolor": "#4CBB17",
        "pressed_bgcolor": "#2e720e",
        "hover_warn_color": "#ffffff",
        "hover_warn_bgcolor": "#D2042D",
        "pressed_warn_bgcolor": "#7d021b",
    }

    def __init__(self):
        super(UI, self).__init__()

        self.setWindowTitle("EPUB Metaclean - V4.0")
        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        self.setMinimumSize(460, 460)

        self.loadStyleSheet()

        self.initUI()

        self.file_watcher = QFileSystemWatcher(["styles.qss"])
        self.file_watcher.fileChanged.connect(self.loadStyleSheet)

    def resizeEvent(self, event):
        self.updateFontSize()
        self.loadStyleSheet()

        super().resizeEvent(event)

    def updateFontSize(self):
        screen = QApplication.primaryScreen()
        screen_size = screen.size()

        self.STYLE_VARIABLES["text_size"] = max(14, screen_size.height() // 70)
        self.STYLE_VARIABLES["header_size"] = max(
            18, screen_size.height() // 30
        )

    def loadStyleSheet(self):
        with open(resource_path("styles.qss"), "r") as styles:
            style_sheet = styles.read()

        for var, value in self.STYLE_VARIABLES.items():
            style_sheet = style_sheet.replace(f"{{{var}}}", str(value))

        self.setStyleSheet(style_sheet)

    def initUI(self):
        self.base = Container(name="base")
        self.base.setMargins(*self.DEFAULT_MARGIN)
        self.setCentralWidget(self.base.W)

        self.initProgressBar()
        self.initTaskLabel()
        self.initFiller()
        self.initTaskBtns()
        self.initWebEngine()
        self.initNavBtns()
        self.initConfirmBtns()
        self.initStatus()

        self.showMaximized()
        self.show()

    def initProgressBar(self):
        self.progress_box = Container(self.base, "progress_box", verticle=False)
        self.progress_box.setMargins(*self.DEFAULT_MARGIN)

        self.progress_label = Label(
            self.progress_box, "progress_label", "Progress: "
        )
        self.progress_bar = ProgressBar(
            self.progress_box,
            "progress_bar",
            hor_policy=self.EXPANDING,
        )

        self.progress_box.hide()

    def initTaskLabel(self):
        self.task_label_box = Container(self.base, "task_label_box")
        self.task_label_box.setMargins(*self.DEFAULT_MARGIN)

        self.task_label = Label(self.task_label_box, "task_label")
        self.task_label.setAlignment(Qt.AlignCenter)
        self.task_label_box.hide()

    def initFiller(self):
        self.filler_box = Container(
            self.base, "filler_box", ver_policy=self.EXPANDING
        )

        self.filler_box.hide()

    def initTaskBtns(self):
        self.task_btns_box = Container(
            self.base, "task_btns_box", ver_policy=self.EXPANDING
        )
        self.task_btns_box.setMargins(*self.DEFAULT_MARGIN)

        self.download_book_btn = PushButton(
            self.task_btns_box, "download_book_btn", "Download New Books"
        )
        self.process_books_btn = PushButton(
            self.task_btns_box, "process_books_btn", "Process Existing Books"
        )
        self.upload_books_btn = PushButton(
            self.task_btns_box, "upload_books_btn", "Upload Existing Books"
        )

    def initWebEngine(self):
        self.web_engine_box = Container(
            self.base, "web_engine_box", ver_policy=self.EXPANDING
        )
        self.web_engine_box.setMargins(*self.DEFAULT_MARGIN)

        self.web_engine = WebEngineView(self.web_engine_box, "web_engine")

        self.web_engine_box.hide()

    def initNavBtns(self):
        self.nav_btns_box = Container(self.base, "nav_btns_box")
        self.nav_btns_box.setMargins(*self.DEFAULT_MARGIN)

        self.nav_btns_top = Container(
            self.nav_btns_box, "nav_btns_top", verticle=False
        )
        self.prev_button = PushButton(self.nav_btns_top, "prev_button", "PREV")
        self.select_button = PushButton(
            self.nav_btns_top, "select_button", "SELECT"
        )
        self.next_button = PushButton(self.nav_btns_top, "next_buton", "NEXT")

        self.nav_btns_bottom = Container(self.nav_btns_box, verticle=False)
        self.manual_button = PushButton(
            self.nav_btns_bottom, "manual_button", "Manual"
        )
        self.cancel_button = PushButton(
            self.nav_btns_bottom, "cancel_button", "Cancel", warn=True
        )

        self.nav_btns_box.hide()

    def initConfirmBtns(self):
        self.confirm_box = Container(self.base, "confirm_box", verticle=False)
        self.confirm_box.setMargins(*self.DEFAULT_MARGIN)

        self.true_button = PushButton(self.confirm_box, "true_button", "YES")
        self.false_button = PushButton(
            self.confirm_box, "false_button", "NO", warn=True
        )

        self.confirm_box.W.setVisible(False)

    def initStatus(self):
        self.status_box = Container(self.base, "status_box", verticle=False)
        self.status_box.setMargins(*self.DEFAULT_MARGIN)

        self.status_label = Label(self.status_box, "status_label", "Status: ")
        self.status = Label(
            self.status_box, "status", hor_policy=self.EXPANDING
        )

        self.status_box.hide()

    def updateProgressBar(self, value=1, range=None, override=False):
        if range:
            self.progress_bar.setRange(0, range)
            self.progress_bar.setValue(value)
        else:
            if override:
                self.progress_bar.setValue(value)
            else:
                self.progress_bar.setValue(self.progress_bar.value() + value)


class Book:

    def __init__(self):
        self.title = None
        self.author = None
        self.series = None
        self.series_index = None
        self.cover = None
        self.cover_url = None
        self.cover_id = None
        self.goodreads_url = None
        self.goodreads_id = None
        self.oceanofpdf_url = None
        self.oceanofpdf_has_epub = True
        self.file_name = None

    def __str__(self):
        return f"{self.title} By {self.author}"


class C:
    OCEANOFPDF_URL = "https://oceanofpdf.com/"


# endregion


# region General Helpers
def setup():
    ui.download_book_btn.clicked.connect(start_download_books)
    ui.process_books_btn.clicked.connect(start_process_books)
    ui.upload_books_btn.clicked.connect(start_upload_books)


# endregion


# region UI Helpers
def hideUi():
    ui.progress_box.hide()
    ui.task_label_box.hide()
    ui.filler_box.hide()
    ui.task_btns_box.hide()
    ui.web_engine_box.hide()
    ui.nav_btns_box.hide()
    ui.confirm_box.hide()
    ui.status_box.hide()


# endregion


# region Task Functions
def start_download_books():
    hideUi()
    ui.task_label_box.show()
    ui.task_label.setText("Please Search For A Book:")

    ui.web_engine_box.show()
    ui.web_engine.setUrl(QUrl(C.OCEANOFPDF_URL))


def start_process_books():
    print("process")


def start_upload_books():
    print("upload")


# endregion


# region Main
if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui = UI()

    setup()

    sys.exit(app.exec())

# endregion
