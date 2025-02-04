import sys
import os
import re
import epubfile
import ebookmeta
import requests
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtNetwork import *


class V:
    OCEANOFPDF_URL = "https://oceanofpdf.com/"
    STRING_TO_REMOVE = "OceanofPDF.com"
    GOODREADS_URL = "https://www.goodreads.com/"
    IMAGE_PROVIDER_URL = "https://www.google.com/search?tbm=isch&q="
    PLAY_BOOKS = "https://play.google.com/books"

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

    def deleteChildren(self):
        for child in self.W.findChildren(QWidget):
            child.setParent(None)
            child.deleteLater()

    def deleteSelf(self):
        if self.W is not None:
            self.deleteChildren()
            self.W.setParent(None)
            self.W.deleteLater()


class ScrollArea:
    def __init__(
        self,
        parent=None,
        name=None,
        verticle=True,
        hor_policy=None,
        ver_policy=None,
    ):
        self.W = QScrollArea(parent.W) if parent else QScrollArea()
        self.W.setObjectName(name)
        self.W.setWidgetResizable(True)

        self.container = Container(
            None,
            name + "_area",
            verticle=verticle,
            hor_policy=hor_policy,
            ver_policy=ver_policy,
        )

        self.container.setMargins(0)
        self.W.setWidget(self.container.W)

        if parent is not None:
            parent.add(self.W)

    def add(self, widget, *args, **kwargs):
        self.container.add(widget, *args, **kwargs)

    def setSpacing(self, spacing=0):
        self.container.L.setSpacing(spacing)

    def setMargins(self, left=None, top=None, right=None, bottom=None):
        curr_left, curr_top, curr_right, curr_bottom = (
            self.W.getContentsMargins()
        )

        left = left if left is not None else curr_left
        top = top if top is not None else curr_top
        right = right if right is not None else curr_right
        bottom = bottom if bottom is not None else curr_bottom

        self.W.setContentsMargins(left, top, right, bottom)

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

    def warn(self, warn):
        self.setProperty("theme", "warn" if warn else None)


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
        self.setWordWrap(True)

        hor_policy = hor_policy if hor_policy is not None else self.PREFERRED
        ver_policy = ver_policy if ver_policy is not None else self.PREFERRED
        self.setSizePolicy(hor_policy, ver_policy)

        parent.add(self)

    def warn(self, warn):
        self.setProperty("theme", "warn" if warn else None)


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
        self.context_menu_enabled = True
        self.image_select_callback = None

    def acceptNavigationRequest(self, url, _type, isMainFrame):
        if self.interceptor:
            return self.interceptor(url)

        return True


class WebEngineView(QWebEngineView):
    PREFERRED = QSizePolicy.Policy.Preferred

    def __init__(self, parent, name=None, hor_policy=None, ver_policy=None):
        super(WebEngineView, self).__init__(parent.W)
        self.setObjectName(name)

        self.context_menu_enabled = False
        self.image_select_callback = None

        self.web_page = WebEnginePage(parent.W)
        self.setPage(self.web_page)

        hor_policy = hor_policy if hor_policy is not None else self.PREFERRED
        ver_policy = ver_policy if ver_policy is not None else self.PREFERRED
        self.setSizePolicy(hor_policy, ver_policy)

        parent.add(self)

    def setInterceptor(self, interceptor):
        self.web_page.interceptor = interceptor

    def contextMenuEvent(self, event):
        self.menu = QMenu()
        if self.context_menu_enabled:
            hit_test = self.web_page.contextMenuData()

            if hit_test.mediaType() == QWebEngineContextMenuData.MediaTypeImage:
                image_url = hit_test.mediaUrl().toString()

                if image_url.lower().endswith((".jpg", ".jpeg", ".png")):
                    select_action = QAction("Select", self.menu)

                    def handleImage():
                        clipboard = QApplication.clipboard()
                        clipboard.clear()

                        self.triggerPageAction(
                            QWebEnginePage.CopyImageToClipboard
                        )

                        QTimer.singleShot(100, processImage)

                    def waitForClipboardContent(attempts=10):
                        clipboard = QApplication.clipboard()
                        qimage = clipboard.image()

                        if not qimage.isNull():
                            processImage()
                        elif attempts > 0:
                            QTimer.singleShot(
                                50,
                                lambda: waitForClipboardContent(attempts - 1),
                            )

                    def processImage():
                        clipboard = QApplication.clipboard()
                        qimage = clipboard.image()
                        buffer = QBuffer()
                        buffer.open(QIODevice.WriteOnly)
                        qimage.save(buffer, "JPEG")
                        buffer.close()
                        image = buffer.data()

                        if not image.isNull() and self.image_select_callback:
                            self.image_select_callback(image)

                    select_action.triggered.connect(handleImage)
                    self.menu.addAction(select_action)

        self.menu.popup(event.globalPos())

    def setContextCall(self, callback=None):
        self.context_menu_enabled = True if callback is not None else False
        self.image_select_callback = callback

    def loaded(self, slot):
        self.loadedDone()

        self.loadFinished.connect(slot)

    def loadedDone(self):
        try:
            self.loadFinished.disconnect()
        except TypeError:
            pass

    def setUrl(self, url):
        url = QUrl(url)
        super().setUrl(url)
        # self.loaded(self.clearHistory)

    def clearHistory(self):
        self.history().clear()

    def createWindow(self, _type):
        return self

    def downloadReq(self, slot):
        try:
            self.page().profile().downloadRequested.disconnect()
        except TypeError:
            pass

        self.page().profile().downloadRequested.connect(slot)

    def deleteSelf(self):
        if self is not None:
            self.setParent(None)
            self.deleteLater()


class UI(QMainWindow):
    DEFAULT_MARGIN = 3, 3, 3, 3
    EXPANDING = QSizePolicy.Expanding
    MINIMUM = QSizePolicy.Minimum
    STYLE_VARIABLES = {
        "text_size": "12px",
        "btn_text_color": "#000000",
        "btn_text_alt_color": "#ffffff",
        "primary_color": "#4CBB17",
        "primary_dark_color": "#358310",
        "secondary_color": "#D8D4D5",
        "secondary_dark_color": "#9b9193",
        "warn_color": "#D32926",
        "warn_dark_color": "#941d1b",
        "bg_color": "#323232",
        "bg_alt_color": "#6f6f6f",
        "border": "2px solid #ffffff",
        "border_alt": "0 solid #ffffff",
        "border_radius": "10px",
    }

    def __init__(self):
        super(UI, self).__init__()

        self.setWindowTitle("EPUB Metaclean - V4.0")
        self.setWindowIcon(QIcon(resourcePath("icon.ico")))
        self.setMinimumSize(460, 460)

        self.initUI()

        self.file_watcher = QFileSystemWatcher(["styles.qss"])
        self.file_watcher.fileChanged.connect(self.loadStyleSheet)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateFontSize()
        self.loadStyleSheet()
        self.updateImageSize()
        self.loadRoundedMask()

    def updateFontSize(self):
        screen = QApplication.primaryScreen()
        screen_size = screen.size()

        self.STYLE_VARIABLES["text_size"] = (
            str(max(14, screen_size.height() // 70)) + "px"
        )

    def updateImageSize(self):
        if self.notice_label_image.isVisible() and hasattr(
            self, "notice_label_image_original"
        ):
            image_scaled = self.notice_label_image_original.scaled(
                self.notice_label_image.size(), Qt.KeepAspectRatio
            )

            self.notice_label_image.setPixmap(image_scaled)

    def loadStyleSheet(self):
        with open(resourcePath("styles.qss"), "r") as styles:
            style_sheet = styles.read()

        for var, value in self.STYLE_VARIABLES.items():
            style_sheet = style_sheet.replace(f"{{{var}}}", str(value))

        self.setStyleSheet(style_sheet)

    def loadRoundedMask(self):
        radius = int(self.STYLE_VARIABLES["border_radius"].replace("px", ""))

        path = QPainterPath()
        rect = QRectF(self.web_engine.rect())
        path.addRoundedRect(rect, radius, radius)

        region = QRegion(path.toFillPolygon().toPolygon())
        self.web_engine.setMask(region)

    def initUI(self):
        self.base = Container(name="base")
        self.base.setMargins(*self.DEFAULT_MARGIN)
        self.setCentralWidget(self.base.W)

        self.initTaskLabel()
        self.initProgressBar()
        self.initCurrentFileLabel()
        self.initNoticeLabel()
        self.initTaskBtns()
        self.initProcessList()
        self.initProcessOptions()
        self.initWebEngine()
        self.initNavBtns()
        self.initConfirmBtns()
        self.initContinuehbtn()
        self.initStatus()
        self.initHiddenWebEngineContainer()

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
        self.progress_label.setWordWrap(False)
        self.progress_bar = ProgressBar(
            self.progress_box,
            "progress_bar",
            hor_policy=self.EXPANDING,
        )

        self.progress_box.hide()

    def initCurrentFileLabel(self):
        self.current_file_box = Container(self.base, "current_file_box")
        self.current_file_box.setMargins(*self.DEFAULT_MARGIN)

        self.current_file_label = Label(self.current_file_box)
        self.current_file_box.hide()

    def initNoticeLabel(self):
        self.notice_label_box = Container(
            self.base, "notice_label_box", ver_policy=self.EXPANDING
        )
        self.notice_label_box.setSpacing(40)

        self.notice_label_title = Label(self.notice_label_box, text="")
        self.notice_label_title.setAlignment(Qt.AlignCenter)

        self.notice_label_image = Label(
            self.notice_label_box, ver_policy=self.EXPANDING
        )
        self.notice_label_image.setAlignment(Qt.AlignCenter)
        self.notice_label_image.setScaledContents(False)
        self.notice_label_image.hide()

        self.notice_label = Label(self.notice_label_box)
        self.notice_label.setAlignment(Qt.AlignCenter)

        self.notice_label_box.hide()

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

    def initProcessList(self):
        self.process_list_box = ScrollArea(
            self.base, "process_list_box", ver_policy=self.EXPANDING
        )

        self.process_list_box.setMargins(*self.DEFAULT_MARGIN)
        self.process_list_box.setSpacing(5)

        self.process_list_box.hide()

    def initProcessOptions(self):
        self.process_options_box = Container(
            self.base, "process_options_box", verticle=False
        )
        self.process_options_box.setMargins(*self.DEFAULT_MARGIN)

        self.select_downloads_btn = PushButton(
            self.process_options_box, text="Select Downloads"
        )
        self.select_others_btn = PushButton(
            self.process_options_box, text="Select Others"
        )
        self.clear_selections_btn = PushButton(
            self.process_options_box, text="Clear All"
        )

        self.process_options_box.hide()

    def initWebEngine(self):
        self.web_engine_box = Container(
            self.base, "web_engine_box", ver_policy=self.EXPANDING
        )
        self.web_engine_box.setMargins(*self.DEFAULT_MARGIN)

        self.web_engine = WebEngineView(self.web_engine_box, "web_engine")

        self.web_engine_box.hide()

    def initNavBtns(self):
        self.nav_btns_box = Container(self.base, "nav_btns_box", verticle=False)
        self.nav_btns_box.setMargins(*self.DEFAULT_MARGIN)

        self.back_btn = PushButton(self.nav_btns_box, text="Go Back")
        self.back_btn.click(self.web_engine.back)
        self.select_btn = PushButton(self.nav_btns_box, text="Select")
        self.skip_btn = PushButton(self.nav_btns_box, text="Skip", warn=True)

        self.nav_btns_box.hide()

    def initConfirmBtns(self):
        self.confirm_box = Container(self.base, "confirm_box", verticle=False)
        self.confirm_box.setMargins(*self.DEFAULT_MARGIN)

        self.true_btn = PushButton(self.confirm_box, "true_btn", "YES")
        self.false_btn = PushButton(self.confirm_box, "false_btn", "NO")

        self.confirm_box.W.setVisible(False)

    def initContinuehbtn(self):
        self.continue_btn_box = Container(self.base, "continue_btn_box")
        self.continue_btn_box.setMargins(*self.DEFAULT_MARGIN)

        self.continue_btn = PushButton(self.continue_btn_box, "continue_btn")

        self.continue_btn_box.hide()

    def initStatus(self):
        self.status_box = Container(self.base, "status_box", verticle=False)
        self.status_box.setMargins(*self.DEFAULT_MARGIN)

        self.status_label = Label(self.status_box, "status_label", "Status: ")
        self.status = Label(
            self.status_box, "status", hor_policy=self.EXPANDING
        )

        self.status_box.hide()

    def initHiddenWebEngineContainer(self):
        self.hidden_engines_box = Container(self.base)
        self.hidden_engines_box.hide()

    def updateProgressBar(self, value=None, range=None, override=False):
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

    def confirmAction(
        self,
        title,
        text,
        action_true=None,
        action_false=None,
        warn_text=False,
        warn_true=False,
        warn_false=False,
        image=None,
        info=False,
    ):
        self.hideUI()

        if action_true is None:
            action_true = self.restoreUI

        if action_false is None:
            action_false = self.restoreUI

        self.notice_label_box.show()
        self.notice_label_title.setText(title)

        self.notice_label_image.hide()
        if image is not None:
            byte_array = QByteArray(image)
            pixmap = QPixmap()
            pixmap.loadFromData(byte_array)
            self.notice_label_image_original = pixmap
            self.notice_label_image.show()
            self.updateImageSize()

        self.notice_label.setText(text)
        self.notice_label.warn(warn_text)

        self.confirm_box.show()
        self.true_btn.click(lambda: action_true())
        self.false_btn.click(lambda: action_false())
        self.true_btn.warn(warn_true)
        self.false_btn.warn(warn_false)

        if info:
            self.true_btn.setText("OK")
            self.false_btn.hide()
        else:
            self.true_btn.setText("YES")
            self.false_btn.show()

        self.loadStyleSheet()

    def showHome(self):
        self.hideUI()

        self.task_btns_box.show()

    def showBrowserPage(
        self,
        title,
        status_label="Status: ",
        status="Waiting For User Input...",
        url=None,
        interceptor=None,
    ):
        self.hideUI()

        self.task_label_box.show()
        self.task_label.setText(title)

        self.web_engine_box.show()
        self.web_engine.setUrl(url) if url is not None else None
        if interceptor is not None:
            self.web_engine.setInterceptor(interceptor)

        self.status_box.show()
        self.status_label.setText(status_label)
        self.status.setText(status)

        QTimer.singleShot(50, self.loadRoundedMask)

    def showListPage(
        self, title, status_label="Status: ", status="Waiting For User Input..."
    ):
        self.hideUI()

        self.task_label_box.show()
        self.task_label.setText(title)

        ui.process_list_box.container.deleteChildren()
        ui.process_list_box.show()

        ui.process_options_box.show()

        self.status_box.show()
        self.status_label.setText(status_label)
        self.status.setText(status)

    def showTaskPage(
        self, title, status_label="Status: ", status="Processing..."
    ):
        self.hideUI()
        self.process_list_box.container.deleteChildren()

        self.task_label.setText(title)
        self.task_label_box.show()

        self.progress_box.show()

        self.notice_label_box.show()

        self.status_label.setText(status_label)
        self.status.setText(status)
        self.status_box.show()


class Book:
    DEFAULT_MARGIN = 3, 3, 3, 3
    EXPANDING = QSizePolicy.Expanding
    MINIMUM = QSizePolicy.Minimum

    def __init__(self):
        self.title = None
        self.author = None
        self.series = None
        self.series_index = None
        self.cover = None
        self.cover_url = None
        self.cover_id = None
        self.oceanofpdf_url = None
        self.file_name = None
        self.file_path = None

    def __str__(self):
        return f"{self.title} By {self.author}"

    def __eq__(self, other):
        if isinstance(other, Book):
            return self.file_path == other.file_path
        return False

    def initListItem(self, list, action=None):
        self.book_list_item = Container(
            ui.process_list_box.container,
            "book_list_item",
            verticle=False,
            ver_policy=self.MINIMUM,
        )
        self.book_list_item.setMargins(*self.DEFAULT_MARGIN)

        book_details = []

        if self.title is not None:
            book_details.append(f"Title: {self.title}\n")

            if self.author is not None:
                book_details.append(f"Author: {self.title}\n")

            if self.series is not None:
                book_details.append(f"Series: {self.series}\n")

            if self.series_index is not None:
                book_details.append(f"Book: #{self.series_index}")
        else:
            book_details.append(f"File Name: {self.file_name}")

        book_details = "".join(book_details)

        self.list_item_text = Label(
            self.book_list_item, text=book_details, hor_policy=self.EXPANDING
        )

        self.list_item_btn = PushButton(
            self.book_list_item, text=" 🗑 ", warn=True
        )

        self.list_item_btn.click(
            lambda: self.deleteBook(list, action=lambda: action())
        )

    def deleteBook(self, list, delete=None, action=None):
        if delete is None:
            ui.confirmAction(
                "Delete Source File?",
                "Would you like to delete the source file?\n" + self.file_name,
                lambda: self.deleteBook(list, True, action=action),
                lambda: self.deleteBook(list, False, action=action),
                warn_text=True,
                warn_true=True,
            )
            return

        if delete:
            try:
                os.remove(self.file_name)
            except FileNotFoundError:
                pass

        if hasattr(self, "book_list_item"):
            self.book_list_item.deleteSelf()

        if self in list:
            list.remove(self)

        if action is not None:
            action()

    def getFileData(self, file_path=None):
        if file_path is None:
            file_path = self.file_path

        meta = ebookmeta.get_metadata(file_path)
        book = epubfile.Epub(file_path)

        self.title = meta.title.split("(")[0].split(":")[0]
        self.author = meta.author_list_to_string()
        self.series = meta.series if meta.series else None
        self.series_index = meta.series_index if meta.series_index else None

        cover_id = self.getCoverID(book)
        self.cover_id = cover_id if cover_id else None
        self.cover = book.read_file(cover_id) if cover_id else None

        self.file_path = os.path.normpath(file_path)
        self.file_name = os.path.basename(self.file_path)

    def getCoverID(self, book):
        cover_id = None
        false_positives = ["images/cover.png"]
        possible_tags = [
            "coverimagestandard",
            "cover.png",
            "cover-image",
            "cover",
        ]

        try:
            cover_id = book.get_cover_image()
        except:
            pass

        if not cover_id or cover_id in false_positives:
            for tag in possible_tags:
                try:
                    book.get_manifest_item(tag)
                    cover_id = tag
                except:
                    continue

                if cover_id:
                    break

        if not cover_id:
            print("Possible Tags:")

            for item in book.get_manifest_items():
                print(item)

            return None

        return cover_id

    def saveBook(self):
        ui.notice_label_title.setText(f"Saving {self.title}")

        ui.notice_label.setText("Opening Book...")
        meta = ebookmeta.get_metadata(self.file_path)
        ui.updateProgressBar(1)

        ui.notice_label.setText(f"Title: {self.title}")
        meta.title = self.title
        ui.updateProgressBar(1)

        ui.notice_label.setText(f"Author: {self.author}")
        meta.set_author_list_from_string(self.author)
        ui.updateProgressBar(1)

        ui.notice_label.setText(f"Series: {self.series}")
        meta.series = self.series
        ui.updateProgressBar(1)

        ui.notice_label.setText(f"Series: {self.series} #{self.series_index}")
        meta.series_index = self.series_index
        ui.updateProgressBar(1)

        ui.notice_label.setText("Writing File...")
        ebookmeta.set_metadata(self.file_path, meta)
        ui.updateProgressBar(1)

        ui.notice_label.setText(f"Setting Cover...")
        if self.cover_id is not None:
            book_file = epubfile.Epub(self.file_path)
            ui.updateProgressBar(1)
            book_file.write_file(self.cover_id, self.cover)
            ui.updateProgressBar(1)
            book_file.save(self.file_path)
            ui.updateProgressBar(1)


class Downloads:
    def __init__(self):
        self.download_queue = 0
        self.download_count = 0
        self.books = []
        self.download_map = {}
        self.locked = False

        ui.restart_btn.click(
            lambda: ui.confirmAction(
                "Restarting Download Task!",
                "Are you sure you would like to restart the download task?",
                self.restart,
                warn_text=True,
                warn_true=True,
            )
        )

        ui.close_btn.click(
            lambda: ui.confirmAction(
                "Cancelling Download Task!",
                "Are you sure you would like to cancel the download task?",
                self.close,
                warn_text=True,
                warn_true=True,
            )
        )

        ui.continue_btn.setText("Process Downloads")
        ui.continue_btn.click(
            lambda: ui.confirmAction(
                "Process Books?",
                "Are you sure you want to process these books?",
                self.startProcessBooks,
            )
        )

        ui.updateProgressBar(0, 1, True)

        ui.showBrowserPage(
            "Downloading New Books",
            url=v.OCEANOFPDF_URL,
            interceptor=self.urlInterceptor,
        )

    def restart(self):
        ui.hidden_engines_box.deleteChildren()
        startDownloadBooks()

    def close(self):
        ui.hidden_engines_box.deleteChildren()
        close()

    def urlInterceptor(self, url):
        url = str(url.toString())

        url_path = url.replace(v.OCEANOFPDF_URL, "")

        if url_path.startswith("authors/"):
            if self.locked:
                return False

            epub_available = url_path.split("/")[2].replace("pdf-", "")

            if epub_available.startswith("epub"):
                ui.status.setText("EPUB Available, Fetching...")

                if not checkBookExists(self.books, "oceanofpdf_url", url):
                    ui.continue_btn_box.hide()

                    book = Book()
                    book.oceanofpdf_url = url
                    self.books.append(book)

                    download_engine = WebEngineView(ui.hidden_engines_box)

                    self.download_map[download_engine] = book

                    download_engine.downloadReq(self.handleDownload)
                    download_engine.loaded(
                        lambda: self.openBookPage(download_engine)
                    )
                    download_engine.setUrl(url)
                    self.locked = False
                    self.download_queue += 1

                else:
                    ui.status.setText(
                        "Already Downloaded! - Waiting For User Input..."
                    )

                return False

            else:
                ui.status.setText(
                    "EPUB NOT AVAILABLE! - Waiting For User Input..."
                )

            return False

        return True

    def openBookPage(self, download_engine):
        ui.status.setText("Adding Book To Download Queue...")
        ui.continue_btn_box.hide()

        query_tag = "input[type='image'][src^='https://media.oceanofpdf.com/epub-button']"
        js_code = (
            f'var element = document.querySelector("{query_tag}");'
            + "element.click();"
        )

        download_engine.page().runJavaScript(js_code)

    def handleDownload(self, download):
        curr_dir = os.getcwd()
        file_name = str(download.suggestedFileName()).replace(
            "/OceanofPDF.com/", ""
        )

        file_path = os.path.join(curr_dir, file_name)

        download.setDownloadFileName(file_path)
        download.accept()

        ui.progress_box.show()
        ui.updateProgressBar(range=self.download_queue)

        book = self.download_map.get(download.page().view(), None)
        book.file_name = file_name
        book.file_path = file_path

        download.finished.connect(self.downloadComplete)

        ui.status.setText("Waiting For User Input...")

    def downloadComplete(self):
        ui.updateProgressBar(1)

        self.download_count += 1

        if self.download_count == self.download_queue:
            ui.hidden_engines_box.deleteChildren()
            ui.continue_btn_box.show()

    def startProcessBooks(self):
        ui.hidden_engines_box.deleteChildren()
        startProcessBooks(self.books)


class Process:
    def __init__(self, books):
        self.books = []
        self.curr_index = -1

        if not books == False:
            self.books = books
            for book in self.books:
                book.getFileData()

        ui.restart_btn.click(
            lambda: ui.confirmAction(
                "Restarting Processing Task!",
                "Are you sure you would like to restart the process task?",
                self.restart,
                warn_text=True,
                warn_true=True,
            )
        )

        ui.close_btn.click(
            lambda: ui.confirmAction(
                "Cancelling Process Task!",
                "Are you sure you would like to cancel the process task?",
                self.close,
                warn_text=True,
                warn_true=True,
            )
        )

        ui.select_downloads_btn.click(self.getSourceFiles)
        ui.select_others_btn.click(self.getUserFiles)
        ui.clear_selections_btn.click(
            lambda: ui.confirmAction(
                "Clear All Files",
                "Are you sure you would like to clear all files from the list?\nNOTE: The source files will NOT be deleted!",
                self.clearAllFiles,
                warn_text=True,
                warn_true=True,
            )
        )

        ui.continue_btn.click(self.cleanPages)
        ui.continue_btn.setText("Process Books")

        self.initBookSelection()

    def restart(self):
        ui.process_list_box.container.deleteChildren()
        startProcessBooks()

    def close(self):
        ui.process_list_box.container.deleteChildren()
        close()

    def checkSource(self):
        files = [f for f in os.listdir(os.getcwd()) if f.endswith(".epub")]

        if files:
            return True

        return False

    def initBookSelection(self):
        ui.showListPage("Processing Books")

        if len(self.books) > 0:
            self.books.sort(key=lambda book: book.title.lower())

        for book in self.books:
            book.initListItem(
                self.books, action=lambda: self.initBookSelection()
            )

        ui.select_downloads_btn.hide()
        ui.select_downloads_btn.show() if self.checkSource() else None
        ui.clear_selections_btn.hide()

        if len(self.books) > 0:
            ui.clear_selections_btn.show()
            ui.continue_btn_box.show()

    def getSourceFiles(self):
        files = [f for f in os.listdir(os.getcwd()) if f.endswith(".epub")]

        for file in files:
            book = Book()
            book.getFileData(os.path.join(os.getcwd(), file))
            if book not in self.books:
                self.books.append(book)

        self.confirmSourceFiles(0)

    def confirmSourceFiles(self, index):
        if index == len(self.books):
            self.initBookSelection()
            return

        base_text = (
            "Would you like to process this book?\n"
            + self.books[index].file_name
        )
        if self.books[index].cover_id is None:
            base_text = (
                base_text
                + "\n\nWARNING: Cannot update cover image due to file error!"
            )

        ui.confirmAction(
            "Process This Book?",
            base_text,
            lambda: self.confirmSourceFiles(index + 1),
            lambda: self.books[index].deleteBook(
                self.books, action=lambda: self.confirmSourceFiles(index)
            ),
        )

    def getUserFiles(self):
        files, _ = QFileDialog.getOpenFileNames(
            None, "Select Files", "", "EPUB FIles (*.epub)"
        )

        for file in files:
            book = Book()
            book.getFileData(file)
            if book not in self.books:
                self.books.append(book)

        self.initBookSelection()

    def clearAllFiles(self):
        self.books = []
        self.initBookSelection()

    def cleanPages(self):
        ui.showTaskPage("Processing Books", status="Cleaning Books...")

        for book in self.books:
            ui.notice_label_title.setText(f"Cleaning {book.title}...")

            book_file = epubfile.Epub(book.file_path)

            book_pages = len(book_file.get_texts())
            ui.updateProgressBar(0, book_pages, True)

            for index, page in enumerate(book_file.get_texts(), start=1):
                ui.notice_label.setText(f"Page {index} Of {book_pages}")
                soup = book_file.read_file(page)
                soup = re.sub(v.STRING_TO_REMOVE, "", soup, flags=re.IGNORECASE)
                book_file.write_file(page, soup)
                ui.updateProgressBar(1)

            book_file.save(book.file_path)

            ui.updateProgressBar(1)

        self.searchBook()

    def urlInterceptor(self, url):
        url = str(url.toString())

        if url.startswith(v.GOODREADS_URL):
            url_path = url.replace(v.GOODREADS_URL, "")

            if url_path.startswith("book/show/"):
                ui.web_engine.loaded(ui.select_btn.show)
            else:
                try:
                    ui.web_engine.loadFinished.disconnect(ui.select_btn.show)
                except TypeError:
                    pass

                ui.select_btn.hide()

        return True

    def searchBook(self):
        self.curr_index += 1

        if self.curr_index == len(self.books):
            self.curr_index = -1
            self.saveBooks()
            return

        ui.select_btn.click(
            lambda: ui.web_engine.page().toHtml(self.selectBook)
        )

        ui.skip_btn.setText("Skip")
        ui.skip_btn.click(
            lambda: ui.confirmAction(
                "Skip File",
                "Are you sure you want to skip searching for this books details?",
                action_true=self.searchBook,
                warn_text=True,
                warn_true=True,
            )
        )

        replacements = [
            f"_{v.STRING_TO_REMOVE}_",
            "-",
            "_",
            "(",
            ")",
            ".epub",
            " ",
        ]
        query = self.books[self.curr_index].title

        for part in replacements:
            query = query.replace(part, "+")

        ui.showBrowserPage(
            "Processing Books",
            url=f"{v.GOODREADS_URL}search?q={query}",
            interceptor=self.urlInterceptor,
        )

        ui.current_file_box.show()
        ui.current_file_label.setText(
            f"Searching For: {self.books[self.curr_index].title}"
        )

        ui.nav_btns_box.show()

    def selectBook(self, html):
        ui.showTaskPage(
            "Processing Books", status="Pulling Book Data From Page..."
        )

        ui.updateProgressBar(0, 7, True)

        book = self.books[self.curr_index]
        soup = BeautifulSoup(html, "html.parser")

        ui.notice_label_title.setText("Fetching Data:")

        book.title = soup.select(".Text__title1")[0].text.strip()
        ui.notice_label.setText(f"Title: {book.title}")
        ui.updateProgressBar(1)

        book.author = soup.select(".ContributorLink__name")[0].text.strip()
        ui.notice_label.setText(f"Author: {book.author}")
        ui.updateProgressBar(1)

        series_link = soup.select_one(
            'a[href^="https://www.goodreads.com/series"]'
        )
        ui.updateProgressBar(1)

        if series_link:
            book.series = series_link.contents[0].strip()
            book.series_index = series_link.contents[1].strip()
            ui.notice_label.setText(
                f"Series: {book.series} #{book.series_index}"
            )

        ui.updateProgressBar(1)

        if book.cover_id is None:
            self.books[self.curr_index] = book
            ui.updateProgressBar(3)
            self.searchBook()
            return

        book.cover_url = soup.select(".BookCover__image")[0].select("img")[0][
            "src"
        ]
        ui.notice_label.setText(f"Cover URL: {book.cover_url}")
        ui.updateProgressBar(1)

        ui.notice_label.setText(f"Cover: Downloading...")
        book.cover = requests.get(book.cover_url, stream=True).content
        ui.updateProgressBar(1)

        self.books[self.curr_index] = book
        ui.updateProgressBar(1)

        if self.curr_index == 0:
            ui.confirmAction(
                "Cover Instructions",
                "To select a cover image, find an image you like and right click it. If it can be used, there will be a 'Select' option.",
                lambda: self.selectCover(self.books[self.curr_index].cover),
                info=True,
            )
        else:
            self.selectCover(self.books[self.curr_index].cover)

    def selectCover(self, img_data, accepted=None):
        image = resizeCoverImage(img_data)

        if accepted is None:
            ui.confirmAction(
                "Check Cover Image",
                "Are you happy with this cover image?\n"
                + "NOTE: You can search Google Images for a different cover image if you select no.\n"
                + "If the menu doesn't appear, the image is not the correct format.",
                lambda: self.selectCover(image, True),
                lambda: self.selectCover(image, False),
                image=image,
            )
            return

        if accepted:
            self.books[self.curr_index].cover = image
            ui.web_engine.setContextCall()
            self.searchBook()
            return

        ui.web_engine.setContextCall(self.selectCover)

        ui.showBrowserPage(
            "Processing Book",
            url=f"{v.IMAGE_PROVIDER_URL}{self.books[self.curr_index].title}",
        )

        ui.select_btn.hide()
        ui.skip_btn.setText("Goodreads")
        ui.skip_btn.click(
            lambda: self.selectCover(self.books[self.curr_index].cover)
        )
        ui.nav_btns_box.show()

    def saveBooks(self):
        ui.showTaskPage("Processing Books", status="Saving Books...")
        ui.updateProgressBar(0, len(self.books) * 9, True)

        for book in self.books:
            book.saveBook()

        ui.process_list_box.container.deleteChildren()

        ui.confirmAction(
            "Upload Books",
            "Would you like to upload these books to Play Books?",
            lambda: startUploadBooks(self.books),
            close,
        )


class Upload:
    def __init__(self, books):
        self.books = []

        if not books == False:
            self.books = books

        ui.restart_btn.click(
            lambda: ui.confirmAction(
                "Restarting Upload Task!",
                "Are you sure you would like to restart the upload task?",
                self.restart,
                warn_text=True,
                warn_true=True,
            )
        )

        ui.close_btn.click(
            lambda: ui.confirmAction(
                "Cancelling Upload Task!",
                "Are you sure you would like to cancel the upload task?",
                self.close,
                warn_text=True,
                warn_true=True,
            )
        )

        ui.select_downloads_btn.click(self.getSourceFiles)
        ui.select_others_btn.click(self.getUserFiles)
        ui.clear_selections_btn.click(
            lambda: ui.confirmAction(
                "Clear All Files",
                "Are you sure you would like to clear all files from the list?\nNOTE: The source files will NOT be deleted!",
                self.clearAllFiles,
                warn_text=True,
                warn_true=True,
            )
        )

        ui.continue_btn.click(self.startPlayBooksUpload)
        ui.continue_btn.setText("Upload Books")

        self.initBookSelection()

    def restart(self):
        ui.process_list_box.container.deleteChildren()
        startUploadBooks()

    def close(self):
        ui.process_list_box.container.deleteChildren()
        close()

    def getSourceFiles(self):
        files = [f for f in os.listdir(os.getcwd()) if f.endswith(".epub")]

        for file in files:
            book = Book()
            book.getFileData(os.path.join(os.getcwd(), file))
            if book not in self.books:
                self.books.append(book)

        self.confirmSourceFiles(0)

    def confirmSourceFiles(self, index):
        if index == len(self.books):
            self.initBookSelection()
            return

        base_text = (
            "Would you like to upload this book?\n"
            + self.books[index].file_name
        )

        ui.confirmAction(
            "Upload This Book?",
            base_text,
            lambda: self.confirmSourceFiles(index + 1),
            lambda: self.books[index].deleteBook(
                self.books, action=lambda: self.confirmSourceFiles(index)
            ),
        )

    def getUserFiles(self):
        files, _ = QFileDialog.getOpenFileNames(
            None, "Select Files", "", "EPUB FIles (*.epub)"
        )

        for file in files:
            book = Book()
            book.getFileData(file)
            if book not in self.books:
                self.books.append(book)

        self.initBookSelection()

    def clearAllFiles(self):
        self.books = []
        self.initBookSelection()

    def checkSource(self):
        files = [f for f in os.listdir(os.getcwd()) if f.endswith(".epub")]

        if files:
            return True

        return False

    def initBookSelection(self):
        ui.showListPage("Uploading Books")

        if len(self.books) > 0:
            self.books.sort(key=lambda book: book.title.lower())

        for book in self.books:
            book.initListItem(
                self.books, action=lambda: self.initBookSelection()
            )

        ui.select_downloads_btn.hide()
        ui.select_downloads_btn.show() if self.checkSource() else None
        ui.clear_selections_btn.hide()

        if len(self.books) > 0:
            ui.clear_selections_btn.show()
            ui.continue_btn_box.show()

    def startPlayBooksUpload(self, upload_confirmed=False):
        ui.continue_btn_box.hide()

        if not upload_confirmed:
            ui.confirmAction(
                "Upload To Play Books?",
                "Would you like to upload these books to play books?",
                lambda: self.startPlayBooksUpload(True),
                self.close,
            )

        else:
            ui.web_engine.loaded(lambda: self.checkPlayBooksLogin())
            ui.showBrowserPage(
                "Uploading Books To Play Books",
                status="Uploading To Play Books...",
                url=v.PLAY_BOOKS,
            )
            ui.continue_btn.click(lambda: self.startPlayBooksUpload(True))
            ui.continue_btn.setText("I Have Logged In")

    def checkPlayBooksLogin(self, logged_in=None):
        ui.web_engine.loadedDone()

        if logged_in is None:
            js_code = (
                "var element = Array.from(document.querySelectorAll('span.mdc-button__label')).find("
                "el => el.textContent.trim() === 'Upload files');"
                "if (element) { element.click(); true; } else { false; }"
            )

            ui.web_engine.page().runJavaScript(
                js_code, lambda result: self.checkPlayBooksLogin(result)
            )
            return

        if not logged_in:
            query_tag = "a[aria-label='Sign in'][href^='https://accounts.google.com/ServiceLogin']"
            js_code = (
                f'var element = document.querySelector("{query_tag}");'
                + "if (element) {{"
                + "element.click();"
                + "}}"
            )

            ui.web_engine.page().runJavaScript(js_code)

            ui.confirmAction(
                "Login Required",
                "Please login to your google account. Click OK when you are done.",
                lambda: (ui.restoreUI(), ui.continue_btn_box.show()),
                info=True,
            )
            return

        QTimer.singleShot(500, self.uploadToPlayBooks)

    def uploadToPlayBooks(self, position=None):
        if position is None:
            js_code = """
            var iframe = document.querySelector('iframe.picker.modal-dialog-bg');
            if (iframe) {
                var rect = iframe.getBoundingClientRect();
                JSON.stringify({ x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 });
            } else {
                null;
            }
            """

            ui.web_engine.page().runJavaScript(
                js_code,
                lambda result: QTimer.singleShot(
                    500, lambda: self.uploadToPlayBooks(result)
                ),
            )
            return


def resourcePath(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def checkBookExists(books, target_key, target_val):
    return any(getattr(book, target_key, False) == target_val for book in books)


def resizeCoverImage(img_data):
    image = Image.open(BytesIO(img_data))
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    image = image.resize((1600, 2560), Image.Resampling.LANCZOS)

    output = BytesIO()
    image.save(output, format="JPEG", quality=95)

    return output.getvalue()


def setup():
    ui.download_book_btn.click(startDownloadBooks)
    ui.process_books_btn.click(startProcessBooks)
    ui.upload_books_btn.click(startUploadBooks)

    ui.task_btns_box.show()


def close():
    v.download_worker = None
    v.process_worker = None
    v.upload_worker = None

    ui.showHome()


def startDownloadBooks():
    v.download_worker = Downloads()


def startProcessBooks(books=False):
    v.download_worker = None
    v.process_worker = Process(books)


def startUploadBooks(books=False):
    v.upload_worker = None
    v.upload_worker = Upload(books)


if __name__ == "__main__":
    v = V
    app = QApplication(sys.argv)
    ui = UI()

    v.download_worker = None
    v.process_worker = None
    v.upload_worker = None

    setup()

    sys.exit(app.exec())
