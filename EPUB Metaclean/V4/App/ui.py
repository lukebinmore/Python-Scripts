from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from qt_overrides import *
from helper_functions import *
from globals import Globals as G


class BookItem(Container):
    def __init__(self, parent, book, edit_action=None, delete_action=None):
        super().__init__(parent, name="book_list_item", vertical=False, ver_policy=QSizePolicy.Minimum)

        self.book = book
        self.edit_action = edit_action
        self.delete_action = delete_action

        details = self.generateDetails()
        self.item_text = Label(self, text=details, hor_policy=QSizePolicy.Expanding)
        # self.edit_btn = PushButton(self, text=" 📝 ")
        self.delete_btn = PushButton(self, text=" 🗑 ", warn=True)

    def generateDetails(self):
        details = []
        if self.book.title is not None:
            details.append(f"Title: {self.book.title}\n")
            if self.book.author is not None:
                details.append(f"Author: {self.book.author}\n")
            if self.book.series is not None:
                details.append(f"Series: {self.book.series}\n")
            if self.book.series_index is not None:
                details.append(f"Book: #{self.book.series_index}")
        else:
            details.append(f"File Name: {self.book.file_name}")

        return "".join(details)

    def deleteBook(self, ui, book_list, action_true=None, action_false=None):
        cover_exists = False if self.book.cover is None else True
        action_true = action_true or ui.restoreUI()
        action_false = action_false or ui.restoreUI()

        ui.confirmAction(
            "Deleting Book",
            "Would you like to delete the source file?",
            lambda: (action_true(), self.book.deleteBook(book_list, True)),
            lambda: (action_false(), self.book.deleteBook(book_list, False)),
            warn_text=True,
            warn_true=True,
            image=resizeCoverImage(self.book.cover) if cover_exists else None,
        )


class UI(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(G.TITLE)
        self.setWindowIcon(QIcon(resourcePath(G.ICON)))
        self.setMinimumSize(*G.MINIMUM_SIZE)

        self.base = Container(name="base")
        self.setCentralWidget(self.base)

        self.style_variables = G.STYLE_VARIABLES

        self.initUI()
        self.showMaximized()
        self.show()

        self.file_watcher = QFileSystemWatcher([G.STYLES_FILE])
        self.file_watcher.fileChanged.connect(self.loadStyleSheet)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateFontSize()
        self.loadStyleSheet()
        self.updateImageSize()
        self.loadRoundedMask()

    def updateFontSize(self):
        screen_size = QApplication.primaryScreen().size()
        self.style_variables["text_size"] = f"{max(14, screen_size.height()//70)}px"

    def loadStyleSheet(self):
        with open(resourcePath(G.STYLES_FILE), "r") as styles:
            style_sheet = styles.read()

        for var, value in self.style_variables.items():
            style_sheet = style_sheet.replace(f"{{{var}}}", str(value))

        self.setStyleSheet(style_sheet)

    def updateImageSize(self):
        if self.notice_label_image.isVisible() and hasattr(self, "notice_label_image_original"):
            self.notice_label_image_original.setPixmap(
                self.notice_label_image_original.scaled(self.notice_label_image.size(), Qt.KeepAspectRatio)
            )

    def loadRoundedMask(self):
        radius = int(self.style_variables["border_radius"].replace("px", ""))
        path = QPainterPath()
        rect = QRectF(self.web_engine.rect())
        path.addRoundedRect(rect, radius, radius)
        self.web_engine.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def initUI(self):
        def createContainer(name, vertical=True, hor_policy=None, ver_policy=None):
            container = Container(self.base, name, vertical=vertical, hor_policy=hor_policy, ver_policy=ver_policy)
            container.hide()
            return container

        def initTaskLabel():
            self.task_label_box = createContainer("task_label_box", False)
            self.restart_btn = PushButton(self.task_label_box, text=" ↺ ", warn=True)
            self.task_label = Label(self.task_label_box, hor_policy=G.EXPANDING)
            self.task_label.setAlignment(Qt.AlignCenter)
            self.close_btn = PushButton(self.task_label_box, text=" X ", warn=True)

        def initProgressBar():
            self.progress_box = createContainer("progress_box")
            self.progress_bar = ProgressBar(self.progress_box, "progress_bar")

        def initCurrentFileLabel():
            self.current_file_box = createContainer("current_file_box")
            self.current_file_label = Label(self.current_file_box)
            self.current_file_label.setAlignment(Qt.AlignCenter)

        def initNoticeLabel():
            self.notice_label_box = createContainer("notice_label_box", ver_policy=G.EXPANDING)
            self.notice_label_box.setSpacing(40)
            self.notice_label_image = Label(self.notice_label_box, ver_policy=G.EXPANDING)
            self.notice_label_image.setAlignment(Qt.AlignCenter)
            self.notice_label_image.setScaledContents(False)
            self.notice_label_image.hide()
            self.notice_label = Label(self.notice_label_box)
            self.notice_label.setAlignment(Qt.AlignCenter)

        def initTaskBtns():
            self.task_btns_box = createContainer("task_btns_box", ver_policy=G.EXPANDING)
            self.download_task_btn = PushButton(self.task_btns_box, "download_task_btn", "Download New Books")
            self.process_task_btn = PushButton(self.task_btns_box, "process_task_btn", "Process Books")
            self.upload_task_btn = PushButton(self.task_btns_box, "upload_task_btn", "Upload Books")

        def initBookList():
            self.book_list_box = createContainer("book_list_box", ver_policy=G.EXPANDING)
            self.book_list_box.setSpacing(5)

        def initBookOptions():
            self.book_options_box = createContainer("book_options_box", False)
            self.select_downloads_btn = PushButton(self.book_options_box, text="Select Downloadeds")
            self.select_others_btn = PushButton(self.book_options_box, text="Select Other Books")
            self.clear_all_btn = PushButton(self.book_options_box, text="Clear All")

        def initWebEngine():
            self.web_engine_box = createContainer("web_engine_box", ver_policy=G.EXPANDING)
            self.web_engine = WebEngineView(self.web_engine_box, "web_engine")

        def initNavBtns():
            self.nav_btns_box = createContainer("nav_btns_box", False)
            self.back_btn = PushButton(self.nav_btns_box, text="Go Back")
            self.back_btn.click(self.web_engine.back)
            self.select_btn = PushButton(self.nav_btns_box, text="Select")
            self.skip_btn = PushButton(self.nav_btns_box, text="Skip", warn=True)

        def initConfirmBtns():
            self.confirm_box = createContainer("confirm_box", False)
            self.true_btn = PushButton(self.confirm_box, "true_btn", "YES")
            self.false_btn = PushButton(self.confirm_box, "false_btn", "NO")

        def initContinueBtn():
            self.continue_btn_box = createContainer("continue_btn_box")
            self.continue_btn = PushButton(self.continue_btn_box, "continue_btn")

        def initStatus():
            self.status_box = createContainer("status_box", False)
            self.status_label = Label(self.status_box, "status_label", "Status: ")
            self.status = Label(self.status_box, "status", hor_policy=G.EXPANDING)

        def initHiddenWebEngineBox():
            self.hidden_engines_box = createContainer("hidden_engines_box")

        initTaskLabel()
        initProgressBar()
        initCurrentFileLabel()
        initNoticeLabel()
        initTaskBtns()
        initBookList()
        initBookOptions()
        initWebEngine()
        initNavBtns()
        initConfirmBtns()
        initContinueBtn()
        initStatus()
        initHiddenWebEngineBox()

    def hideUI(self):
        self.previous_ui = {w: w.isVisible() for w in self.findChildren(Container) if w.objectName().endswith("_box")}
        for widget in self.previous_ui.keys():
            widget.hide()
        self.base.show()

    def restoreUI(self):
        for widget, was_visabal in self.previous_ui.items():
            widget.setVisible(was_visabal)

    def showHome(self):
        self.hideUI()
        self.task_btns_box.show()

    def preparePage(self, title, status_label=None, status=None):
        self.hideUI()
        self.task_label_box.show()
        self.task_label.setText(title)

        self.status_box.show()
        status_label = status_label if status_label is not None else "Status: "
        self.status_label.setText(status_label)
        status = status if status is not None else "Waiting For User Input..."
        self.status.setText(status)

    def showBrowserPage(self, title, url, status_label=None, status=None, interceptor=None):
        self.preparePage(title, status_label, status)
        self.web_engine_box.show()
        self.web_engine.setUrl(url)
        if interceptor is not None:
            self.web_engine.setInterceptor(interceptor)
            QTimer.singleShot(50, self.loadRoundedMask)

    def showListPage(self, title, status_label=None, status=None):
        self.preparePage(title, status_label, status)
        self.book_list_box.show()
        self.book_options_box.show()

    def showTaskPage(self, title, status_label=None, status=None):
        self.preparePage(title, status_label, status)
        self.progress_box.show()
        self.notice_label_box.show()
        self.notice_label_image.hide()

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
        def setNoticeImage():
            if image is not None:
                byte_array = QByteArray(image)
                pixmap = QPixmap()
                pixmap.loadFromData(byte_array)
                self.notice_label_image_original = pixmap
                self.notice_label_image.show()
                self.updateImageSize()
            else:
                self.notice_label_image.hide()

        self.preparePage(title)
        setNoticeImage()

        self.notice_label.setText(text)
        self.notice_label.warn(warn_text)
        action_true = action_true or self.restoreUI
        action_false = action_false or self.restoreUI
        self.true_btn.setText("OK" if info else "YES")
        self.false_btn.setVisible(not info)
        self.true_btn.warn(warn_true)
        self.false_btn.warn(warn_false)
        self.true_btn.click(lambda: action_true())
        self.false_btn.click(lambda: action_false())
        self.notice_label_box.show()
        self.confirm_box.show()

        self.loadStyleSheet()
