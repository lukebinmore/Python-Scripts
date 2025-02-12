from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from qt_overrides import *
from helper_functions import *
from globals import Globals as G


class UI(QMainWindow):
    class BookItem(Container):
        def __init__(self, ui, book):
            super().__init__(
                ui.book_list_box,
                name="list_item",
                vertical=False,
                ver_policy=QSizePolicy.MinimumExpanding,
            )

            self.ui = ui
            self.book = book

            self.cover = ImageLabel(self)
            self.cover.hide()

            self.details = Container(self, "book_list_item_details", hor_policy=G.EXPANDING)
            self.details.setSpacing(0)
            self.title = Label(self.details)
            self.author = Label(self.details)
            self.series = Label(self.details)
            self.series_index = Label(self.details)
            self.progress_bar = ProgressBar(self.details)
            self.progress_bar.hide()

            self.updateData()

            self.delete_btn = PushButton(self, text=" 🗑 ", warn=True)
            self.delete_btn.click(self.deleteBook)

        def updateData(self):
            self.cover.setImage(self.book.cover)
            self.title.setText(self.book.title)
            self.author.setText(f"Author: {self.book.author}")
            self.series.setText(f"Series: {self.book.series}")
            self.series_index.setText(f"Book: #{self.book.series_index}")

            self.author.setVisible(bool(self.book.author))
            self.series.setVisible(bool(self.book.series))
            self.series_index.setVisible(bool(self.book.series_index))

        def deleteBook(self):
            cover_exists = False if self.book.cover is None else True

            self.ui.confirmAction(
                "Deleting Book",
                "Would you like to delete the source file?",
                lambda: self.book.deleteBook(True),
                lambda: self.book.deleteBook(False),
                warn_text=True,
                warn_true=True,
                image=resizeCoverImage(self.book.cover) if cover_exists else None,
            )

            self.delete()

    def __init__(self):
        super().__init__()

        self.setWindowTitle(G.TITLE)
        self.setWindowIcon(QIcon(resourcePath(G.ICON)))
        self.setMinimumSize(*G.MINIMUM_SIZE)

        self.base = Container(name="base")
        self.base.setMargins(*G.DEFAULT_MARGINS)
        self.setCentralWidget(self.base)

        self.hidden_engines_box = Container(self.base, "hidden_engines_box")
        self.hidden_engines_box.hide()

        self.style_variables = G.STYLE_VARIABLES

        self.initUI()
        self.initNoticePage()
        self.showMaximized()
        self.show()

        self.file_watcher = QFileSystemWatcher([G.STYLES_FILE])
        self.file_watcher.fileChanged.connect(self.loadStyleSheet)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateFontSize()
        self.loadStyleSheet()

    def updateFontSize(self):
        screen_size = QApplication.primaryScreen().size()
        self.style_variables["text_size"] = f"{max(14, screen_size.height()//90)}px"

    def loadStyleSheet(self):
        with open(resourcePath(G.STYLES_FILE), "r") as styles:
            style_sheet = styles.read()

        for var, value in self.style_variables.items():
            style_sheet = style_sheet.replace(f"{{{var}}}", str(value))

        self.setStyleSheet(style_sheet)

    def initUI(self):
        self.content = Container(self.base, "content")

        self.task_label_box = Container(self.content, "task_label_box", False)
        self.restart_btn = PushButton(self.task_label_box, text=" ↺ ", warn=True)
        self.task_label = Label(self.task_label_box, hor_policy=G.EXPANDING)
        self.task_label.setAlignment(Qt.AlignCenter)
        self.close_btn = PushButton(self.task_label_box, text=" X ", warn=True)
        self.task_label_box.hide()

        self.task_btns_box = Container(self.content, "task_btns_box", False)
        self.download_task_btn = PushButton(self.task_btns_box, "download_task_btn", "Download New Books")
        self.process_task_btn = PushButton(self.task_btns_box, "process_task_btn", "Process Books")
        self.upload_task_btn = PushButton(self.task_btns_box, "upload_task_btn", "Upload Books")

        self.center_box = Container(self.content, "center_box", vertical=False, ver_policy=G.EXPANDING)
        self.center_box.setSpacing(5)
        self.web_engine = WebEngineView(self.center_box, "web_engine", hor_policy=G.EXPANDING)
        self.web_engine.hide()
        self.book_list_box = ScrollContainer(self.center_box, "book_list_box")
        self.book_list_box.setSpacing(5)

        self.continue_btn = PushButton(self.content, "continue_btn")
        self.continue_btn.hide()

        self.book_options_box = Container(self.content, "book_options_box", False)
        self.select_downloads_btn = PushButton(self.book_options_box, text="Select Downloadeds")
        self.select_others_btn = PushButton(self.book_options_box, text="Select Other Books")
        self.clear_all_btn = PushButton(self.book_options_box, text="Clear All")

        self.nav_btns_box = Container(self.content, "nav_btns_box", False)
        self.back_btn = PushButton(self.nav_btns_box, text="Go Back")
        self.back_btn.click(self.web_engine.back)
        self.select_btn = PushButton(self.nav_btns_box, text="Select")
        self.skip_btn = PushButton(self.nav_btns_box, text="Skip", warn=True)
        self.nav_btns_box.hide()

        self.status_box = Container(self.content, "status_box", False)
        self.status_label = Label(self.status_box, "status_label", "Status: ")
        self.status = Label(self.status_box, "status", hor_policy=G.EXPANDING)

    def initNoticePage(self):
        self.notice = Container(self.base, "notice", ver_policy=G.EXPANDING)
        self.notice.hide()
        self.notice_title = Label(self.notice, hor_policy=G.EXPANDING)
        self.notice_title.setAlignment(Qt.AlignCenter)
        self.notice_image = ImageLabel(self.notice, ver_policy=G.EXPANDING)
        self.notice_text = Label(self.notice)
        self.notice_text.setAlignment(Qt.AlignCenter)
        self.notice_spacer = Label(self.notice)

        self.confirm_box = Container(self.notice, "confirm_box", False)
        self.true_btn = PushButton(self.confirm_box, "true_btn", "YES")
        self.false_btn = PushButton(self.confirm_box, "false_btn", "NO")

    def showContent(self):
        self.content.show()
        self.notice.hide()

    def showNotice(self):
        self.content.hide()
        self.notice.show()

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
        self.showNotice()
        self.notice_title.setText(title)

        self.notice_image.setImage(image)

        self.notice_text.setText(text)
        self.notice_text.warn(warn_text)

        action_true = action_true or self.showContent
        action_false = action_false or self.showContent
        self.true_btn.setText("OK" if info else "YES")
        self.false_btn.setVisible(not info)
        self.true_btn.warn(warn_true)
        self.false_btn.warn(warn_false)
        self.true_btn.click(lambda: action_true())
        self.false_btn.click(lambda: action_false())

        self.loadStyleSheet()
