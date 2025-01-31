import sys
import os
import asyncio
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtNetwork import *
from time import sleep


class V:
    OCEANOFPDF_URL = "https://oceanofpdf.com/"

    download_worker = None
    process_worker = None
    upload_worker = None


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
        self.setProperty("theme", "warn" if warn else None)
        self.setText(text)

        hor_policy = hor_policy if hor_policy is not None else self.PREFERRED
        ver_policy = ver_policy if ver_policy is not None else self.PREFERRED
        self.setSizePolicy(hor_policy, ver_policy)

        parent.add(self)

    def click(self, slot):
        try:
            self.clicked.disconnect()
        except TypeError:
            pass

        self.clicked.connect(slot)


class Label(QLabel):
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
        super(Label, self).__init__(parent.W)
        self.setObjectName(name)
        self.setProperty("theme", "warn" if warn else None)
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


class WebEnginePage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.interceptor = None

    def acceptNavigationRequest(self, url, _type, isMainFrame):
        if self.interceptor:
            return self.interceptor(url)

        return True


class WebEngineView(QWebEngineView):
    PREFERRED = QSizePolicy.Policy.Preferred

    def __init__(self, parent, name=None, hor_policy=None, ver_policy=None):
        super(WebEngineView, self).__init__(parent.W)
        self.setObjectName(name)

        self.web_page = WebEnginePage(parent.W)
        self.setPage(self.web_page)

        hor_policy = hor_policy if hor_policy is not None else self.PREFERRED
        ver_policy = ver_policy if ver_policy is not None else self.PREFERRED
        self.setSizePolicy(hor_policy, ver_policy)

        parent.add(self)

    def setInterceptor(self, interceptor):
        self.web_page.interceptor = interceptor

    def loaded(self, slot):
        try:
            self.loadFinished.disconnect()
        except TypeError:
            pass

        self.loadFinished.connect(slot)

    def setUrl(self, url):
        url = QUrl(url)
        super().setUrl(url)

    def createWindow(self, _type):
        return self


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
        "warn_color": "#D2042D",
        "hover_warn_color": "#ffffff",
        "hover_warn_bgcolor": "#D2042D",
        "pressed_warn_bgcolor": "#7d021b",
    }

    def __init__(self):
        super(UI, self).__init__()

        self.setWindowTitle("EPUB Metaclean - V4.0")
        self.setWindowIcon(QIcon(resourcePath("icon.ico")))
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
        with open(resourcePath("styles.qss"), "r") as styles:
            style_sheet = styles.read()

        for var, value in self.STYLE_VARIABLES.items():
            style_sheet = style_sheet.replace(f"{{{var}}}", str(value))

        self.setStyleSheet(style_sheet)

    def initUI(self):
        self.base = Container(name="base")
        self.base.setMargins(*self.DEFAULT_MARGIN)
        self.setCentralWidget(self.base.W)

        self.initTaskLabel()
        self.initProgressBar()
        self.initWarnLabel()
        self.initFiller()
        self.initTaskBtns()
        self.initWebEngine()
        self.initNavBtns()
        self.initConfirmBtns()
        self.initFinishbtn()
        self.initStatus()

        self.showMaximized()
        self.show()

    def initTaskLabel(self):
        self.task_label_box = Container(
            self.base, "task_label_box", verticle=False
        )
        self.task_label_box.setMargins(*self.DEFAULT_MARGIN)

        self.restart_btn = PushButton(
            self.task_label_box, text=" ↺ ", warn=True
        )
        self.task_label = Label(
            self.task_label_box, "task_label", hor_policy=self.EXPANDING
        )
        self.task_label.setAlignment(Qt.AlignCenter)
        self.close_btn = PushButton(self.task_label_box, text=" X ", warn=True)

        self.task_label_box.hide()

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

    def initWarnLabel(self):
        self.warn_label_box = Container(self.base, "warn_label_box")
        self.warn_label_box.setSpacing(40)

        self.warn_label_title = Label(
            self.warn_label_box, text="Are You Sure?", warn=True
        )
        self.warn_label_title.setAlignment(Qt.AlignCenter)

        self.warn_label = Label(self.warn_label_box)
        self.warn_label.setAlignment(Qt.AlignCenter)

        self.warn_label_box.hide()

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

        self.task_btns_box.hide()

    def initWebEngine(self):
        self.web_engine_box = Container(
            self.base, "web_engine_box", ver_policy=self.EXPANDING
        )
        self.web_engine_box.setMargins(0)

        self.web_engine = WebEngineView(self.web_engine_box, "web_engine")

        self.web_engine_box.hide()

    def initNavBtns(self):
        self.nav_btns_box = Container(self.base, "nav_btns_box")
        self.nav_btns_box.setMargins(*self.DEFAULT_MARGIN)

        self.nav_btns_top = Container(
            self.nav_btns_box, "nav_btns_top", verticle=False
        )
        self.prev_btn = PushButton(self.nav_btns_top, "prev_btn", "PREV")
        self.select_btn = PushButton(self.nav_btns_top, "select_btn", "SELECT")
        self.next_btn = PushButton(self.nav_btns_top, "next_buton", "NEXT")

        self.nav_btns_bottom = Container(self.nav_btns_box, verticle=False)
        self.manual_btn = PushButton(
            self.nav_btns_bottom, "manual_btn", "Manual"
        )
        self.cancel_btn = PushButton(
            self.nav_btns_bottom, "cancel_btn", "Cancel", warn=True
        )

        self.nav_btns_box.hide()

    def initConfirmBtns(self):
        self.confirm_box = Container(self.base, "confirm_box", verticle=False)
        self.confirm_box.setMargins(*self.DEFAULT_MARGIN)

        self.true_btn = PushButton(self.confirm_box, "true_btn", "YES")
        self.false_btn = PushButton(
            self.confirm_box, "false_btn", "NO", warn=True
        )

        self.confirm_box.W.setVisible(False)

    def initFinishbtn(self):
        self.finish_btn_box = Container(self.base, "finish_btn_box")
        self.finish_btn_box.setMargins(*self.DEFAULT_MARGIN)

        self.finish_btn = PushButton(
            self.finish_btn_box, "finish_btn", "Process Downloads"
        )

        self.finish_btn_box.hide()

    def initStatus(self):
        self.status_box = Container(self.base, "status_box", verticle=False)
        self.status_box.setMargins(*self.DEFAULT_MARGIN)

        self.status_label = Label(self.status_box, "status_label", "Status: ")
        self.status = Label(
            self.status_box, "status", hor_policy=self.EXPANDING
        )

        self.status_box.hide()

    def updateProgressBar(
        self, value=None, range=None, text=None, override=False
    ):

        self.progress_label.setText(text) if text is not None else None
        self.progress_bar.setRange(0, range) if range is not None else None

        if override:
            self.progress_bar.setValue(value) if value is not None else None
            return

        if value is not None:
            self.progress_bar.setValue(self.progress_bar.value() + value)

    def hideUI(self):
        self.previous_ui = {
            widget: widget.isVisible()
            for widget in self.findChildren(QFrame)
            if widget.objectName().endswith("_box")
        }

        for widget in self.previous_ui.keys():
            widget.hide()

        ui.base.show()

    def restoreUI(self):
        for widget, was_visable in self.previous_ui.items():
            widget.setVisible(was_visable)

    def confirmAction(self, title, text, action):
        self.hideUI()

        self.warn_label_box.show()
        self.warn_label_title.setText(title)
        self.warn_label.setText(text)

        self.filler_box.show()

        self.confirm_box.show()

        self.true_btn.click(lambda: action())
        self.false_btn.click(self.restoreUI)

    def goHome(self):
        self.hideUI()
        self.task_btns_box.show()


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
        self.file_path = None

    def __str__(self):
        return f"{self.title} By {self.author}"


class Downloads:
    def __init__(self):
        self.download_queue = 0
        self.download_count = 0
        self.adding_book = False
        self.books = []

        ui.hideUI()
        ui.restart_btn.click(
            lambda: ui.confirmAction(
                "Restarting Download Task!",
                "Are you sure you would like to restart the download process?",
                self.restart,
            )
        )

        ui.task_label_box.show()
        ui.task_label.setText("Downloading New Books")

        ui.updateProgressBar(0, 1, "Progress: ", True)
        ui.finish_btn.click(
            lambda: ui.confirmAction(
                "Process Books?",
                "Are you sure you want to process these books?",
                self.startProcessing,
            )
        )

        ui.web_engine.setInterceptor(self.urlInterceptor)
        ui.web_engine_box.show()
        ui.web_engine.setUrl(v.OCEANOFPDF_URL)

        self.hidden_web_engine = WebEngineView(ui.base)
        self.hidden_web_engine.page().profile().downloadRequested.connect(
            self.handleDownload
        )

        ui.status_box.show()
        ui.status.setText("Waiting For User Input...")

    def restart(self):
        startDownloadBooks()

    def urlInterceptor(self, url):
        url = url.toString()

        url_path = str(url).replace(v.OCEANOFPDF_URL, "")

        if self.adding_book:
            ui.status.setText("Please Wait...")
            return False

        if url_path.startswith("authors/"):
            epub_available = url_path.split("/")[2].replace("pdf-", "")

            if epub_available.startswith("epub"):
                ui.status.setText("EPUB Available, Fetching...")

                ui.finish_btn_box.hide()

                book = Book()
                if not checkBookExists(self.books, "oceanofpdf_url", url):
                    self.books.append(book)
                    self.books[-1].oceanofpdf_url = url
                    self.hidden_web_engine.loaded(self.openBookPage)
                    self.hidden_web_engine.setUrl(url)
                else:
                    ui.status.setText(
                        "Already Downloaded!\nWaiting For User Input..."
                    )

                return False

            ui.status.setText("EPUB NOT AVAILABLE!\nWaiting For User Input...")
            return False
        else:
            ui.status.setText("Waiting For User Input...")

        return True

    def openBookPage(self):
        ui.status.setText("Adding Book To Download Queue...")
        self.adding_book = True

        query_tag = "input[type='image'][src^='https://media.oceanofpdf.com/epub-button']"
        js_code = f'document.querySelector("{query_tag}").click();'

        self.hidden_web_engine.page().runJavaScript(js_code)

    def handleDownload(self, download):
        curr_dir = os.getcwd()
        file_name = str(download.suggestedFileName()).replace(
            "/OceanofPDF.com/", ""
        )

        file_path = os.path.join(curr_dir, file_name)

        download.setDownloadFileName(file_path)
        download.accept()

        self.download_queue += 1
        ui.progress_box.show()
        ui.updateProgressBar(
            range=self.download_queue,
            text=f"Downloading {self.download_queue} Files: ",
        )

        self.books[-1].file_name = file_name
        self.books[-1].file_path = file_path

        download.finished.connect(self.downloadComplete)

        self.adding_book = False
        ui.status.setText("Waiting For User Input...")

    def downloadComplete(self):
        ui.updateProgressBar(1)

        self.download_count += 1

        if self.download_count == self.download_queue:
            ui.updateProgressBar(
                text=f"Downloaded {self.download_count} Books: "
            )

            ui.finish_btn_box.show()

    def startProcessing(self):
        startProcessBooks(self.books)


def resourcePath(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def checkBookExists(books, target_key, target_val):
    return any(getattr(book, target_key, False) == target_val for book in books)


def setup():
    ui.download_book_btn.click(startDownloadBooks)

    ui.close_btn.click(
        lambda: ui.confirmAction(
            "Cancelling Download Task!",
            "Are you sure you would like to cancel the download process?",
            close,
        )
    )

    ui.task_btns_box.show()


def close():
    v.download_worker = None
    v.process_worker = None
    v.upload_worker = None

    ui.goHome()


def startDownloadBooks():
    v.download_worker = Downloads()


def startProcessBooks(downloaded_books):
    ui.hide()
    v.download_worker = None
    print("Process Books")


if __name__ == "__main__":
    v = V
    app = QApplication(sys.argv)
    ui = UI()

    v.download_worker = None
    v.process_worker = None
    v.upload_worker = None

    setup()

    sys.exit(app.exec())
