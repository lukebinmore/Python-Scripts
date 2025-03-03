from PyQt5.QtCore import QFileSystemWatcher, Qt, QTimer
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5.QtGui import QIcon
from qt_overrides import (
    Container,
    ImageButton,
    Label,
    ProgressBar,
    PushButton,
    WebEngineView,
    ScrollContainer,
    ImageLabel,
)
from helper_functions import resourcePath
import os
from globals import G


class UI(QMainWindow):
    class BookItem(Container):
        def __init__(self, ui, book, insert_index):
            super().__init__(
                ui.book_list_box.container,
                name="list_item",
                vertical=False,
                insert_index=insert_index,
            )
            self.setMargins(*G.DEFAULT_MARGINS)
            self.ui = ui
            self.book = book

            self.requeue_btn = PushButton(self, text=" ↺ ", theme="warn")
            self.requeue_btn.click(self.requeueBook)
            self.requeue_btn.hide()

            self.cover = ImageButton(self, "list_item_cover")
            self.cover.click(
                lambda: ui.confirmAction(
                    title=self.book.title, image=self.book.cover, info=True
                )
            )

            self.details = Container(self, hor_policy=G.EXPANDING)
            self.details.setSpacing(0)
            self.title = Label(self.details)
            self.author = Label(self.details)
            self.series = Label(self.details)
            self.series_index = Label(self.details)
            self.progress_bar = ProgressBar(self.details)
            self.progress_bar.hide()

            self.updateData()

            self.delete_btn = PushButton(self, text=" 🗑 ", theme="warn")
            self.delete_btn.click(self.deleteBook)

        def updateData(self):
            if self.ui.notice.isVisible():
                QTimer.singleShot(100, self.updateData)
                return

            if not G.download_worker and not G.upload_worker:
                self.requeue_btn.setVisible(bool(self.book.meta_updated))
            else:
                self.requeue_btn.hide()

            self.cover.setImage(self.book.cover)
            self.cover.setVisible(bool(self.book.cover))
            self.title.setText(self.book.title or self.book.file_name)
            self.author.setText(
                f"Author: {self.book.author}"
                if self.book.author is not None
                else None
            )
            self.series.setText(
                f"Series: {self.book.series}"
                if self.book.series is not None
                else None
            )
            self.series_index.setText(
                f"Book: #{self.book.series_index}"
                if self.book.series_index is not None
                else None
            )

            if self.progress_bar.value() == self.progress_bar.maximum():
                self.progress_bar.hide()

        def deleteBook(self):
            cover_exists = False if self.book.cover is None else True
            self.ui.confirmAction(
                "Deleting Book",
                "Would you like to delete the source file?",
                lambda: (self.book.deleteBook(True)),
                lambda: (self.book.deleteBook(False)),
                warn_text=True,
                warn_true=True,
                image=self.book.cover if cover_exists else None,
            )

        def requeueBook(self):
            self.book.requeue = True
            self.requeue_btn.hide()

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
        self.show_requeue = False

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
        self.style_variables["text_size"] = (
            f"{max(14, screen_size.height()//90)}px"
        )

    def loadStyleSheet(self):
        with open(resourcePath(G.STYLES_FILE), "r") as styles:
            style_sheet = styles.read()

        for var, value in self.style_variables.items():
            style_sheet = style_sheet.replace(f"{{{var}}}", str(value))

        self.setStyleSheet(style_sheet)

    def initUI(self):
        self.content = Container(self.base, "content")

        self.task_label_box = Container(self.content, "task_label_box", False)
        self.restart_btn = PushButton(
            self.task_label_box, text=" ↺ ", theme="warn"
        )
        self.task_label = Label(self.task_label_box, hor_policy=G.EXPANDING)
        self.task_label.setAlignment(Qt.AlignCenter)
        self.close_btn = PushButton(
            self.task_label_box, text=" X ", theme="warn"
        )
        self.task_label_box.hide()

        self.task_btns_box = Container(self.content, "task_btns_box", False)
        self.download_task_btn = PushButton(
            self.task_btns_box, "download_task_btn", "Download New Books"
        )
        self.process_task_btn = PushButton(
            self.task_btns_box, "process_task_btn", "Process Books"
        )
        self.upload_task_btn = PushButton(
            self.task_btns_box, "upload_task_btn", "Upload Books"
        )

        self.center_box = Container(
            self.content, "center_box", vertical=False, ver_policy=G.EXPANDING
        )
        self.center_box.setSpacing(5)
        self.web_engine = WebEngineView(
            self.center_box, "web_engine", hor_policy=G.EXPANDING
        )
        self.web_engine.hide()
        self.book_list_box = ScrollContainer(self.center_box, "book_list_box")
        self.book_list_box.container.setSpacing(5)
        self.book_list_box.setMinimumWidth(G.MINIMUM_SIZE[0])
        self.book_list_spacer = Label(
            self.book_list_box.container,
            "book_list_spacer",
            ver_policy=G.EXPANDING,
        )

        self.book_options_box = Container(
            self.content, "book_options_box", False
        )
        self.select_downloads_btn = PushButton(
            self.book_options_box, text="Select Downloadeds"
        )
        self.select_others_btn = PushButton(
            self.book_options_box, text="Select Other Books"
        )
        self.clear_all_btn = PushButton(
            self.book_options_box, text="Clear All", theme="warn"
        )

        self.nav_btns_box = Container(self.content, "nav_btns_box", False)
        self.back_btn = PushButton(self.nav_btns_box, text="Go Back")
        self.back_btn.click(self.web_engine.back)
        self.nav_btn_1 = PushButton(self.nav_btns_box)
        self.nav_btn_2 = PushButton(self.nav_btns_box)
        self.nav_btns_box.hide()

        self.status_box = Container(self.content, "status_box", False)
        self.status_label = Label(self.status_box, "status_label", "Status: ")
        self.status = Label(
            self.status_box,
            "status",
            "Waiting For User Input...",
            hor_policy=G.EXPANDING,
        )

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
        self.updateUIParts()
        self.notice.hide()

    def showNotice(self):
        self.content.hide()
        self.notice.show()

    def confirmAction(
        self,
        title,
        text=None,
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
        self.notice_text.setTheme("warn" if warn_text else None)

        action_true = action_true if action_true else print
        action_false = action_false if action_false else print

        self.true_btn.setText("OK" if info else "YES")
        self.false_btn.setVisible(not info)
        self.true_btn.setTheme("warn" if warn_true else None)
        self.false_btn.setTheme("warn" if warn_false else None)
        self.true_btn.click(
            lambda: (QTimer.singleShot(50, action_true), self.showContent())
        )
        self.false_btn.click(
            lambda: (QTimer.singleShot(50, action_false), self.showContent())
        )

        self.loadStyleSheet()

    def updateUIParts(self):
        if self.notice.isVisible():
            QTimer.singleShot(100, self.updateUIParts)
            return

        QTimer.singleShot(
            50,
            lambda: (
                self.loadStyleSheet(),
                updateBookList(),
                updateSelectDownloadsBtn(),
                updateListSpecificBtns(),
                updateTaskBtns(),
                updateNavBtn1(),
                updateNavBtn2(),
                updateNavBtns(),
                updateTaskLabel(),
                updateBookList(),
            ),
        )

        def updateBookList():
            self.book_list_box.hide()
            if G.download_worker and not G.books:
                return
            self.book_list_box.show()

        def updateSelectDownloadsBtn():
            self.select_downloads_btn.hide()
            files = [f for f in os.listdir(os.getcwd()) if f.endswith(".epub")]
            if not files:
                return
            self.select_downloads_btn.show()

        def updateListSpecificBtns():
            self.process_task_btn.hide()
            self.upload_task_btn.hide()
            self.clear_all_btn.hide()
            if not G.books:
                return
            self.process_task_btn.show()
            self.upload_task_btn.show()
            self.clear_all_btn.show()

        def updateTaskBtns():
            self.task_btns_box.hide()
            self.book_options_box.hide()
            if G.download_worker or G.process_worker or G.upload_worker:
                return
            self.task_btns_box.show()
            self.book_options_box.show()

        def updateNavBtn1():
            self.nav_btn_1.hide()
            if G.download_worker is not None:
                if not G.books:
                    return
                if any(book.download is None for book in G.books):
                    return
                if any(
                    book.download and not book.download.isFinished()
                    for book in G.books
                ):
                    return

            if G.process_worker is not None:
                if not G.process_worker.show_select:
                    return
            self.nav_btn_1.show()

        def updateNavBtn2():
            self.nav_btn_2.hide()
            if G.download_worker is not None:
                return
            self.nav_btn_2.show()

        def updateNavBtns():
            self.nav_btns_box.hide()
            if not self.web_engine.isVisible():
                return
            self.nav_btns_box.show()

        def updateTaskLabel():
            self.task_label_box.hide()
            if G.download_worker is not None:
                self.task_label.setText("Downloading New Books")
            if G.process_worker is not None:
                self.task_label.setText("Processing Books")
            if G.upload_worker is not None:
                self.task_label.setText("Uploading Books")

            if (
                not G.download_worker
                and not G.process_worker
                and not G.upload_worker
            ):
                return
            self.task_label_box.show()

        def updateBookList():
            for book in G.books:
                if book.list_item is not None:
                    book.list_item.updateData()
