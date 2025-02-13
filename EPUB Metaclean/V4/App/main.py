import sys
from globals import Globals as G
from ui import UI
from book_class import Book
from helper_functions import *
from qt_overrides import WebEngineView
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt5.QtCore import QTimer, pyqtSignal

from qt_overrides import *


class Downloads:
    def __init__(self):
        self.download_queue = 0
        self.download_count = 0
        self.download_map = {}
        self.locked = False

        self.windows = []

        self.setupUI()

    def setupUI(self):
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
                "Are you sure you would like to end the download task?",
                self.close,
                warn_text=True,
                warn_true=True,
            )
        )

        ui.continue_btn.setText("Done")
        ui.continue_btn.click(self.close)

        ui.task_btns_box.hide()
        ui.book_options_box.hide()

        ui.task_label_box.show()
        ui.task_label.setText("Downloading New Books")

        ui.web_engine.show()
        ui.web_engine.setInterceptor(self.urlInterceptor)
        ui.web_engine.setUrl(G.OCEANOFPDF_URL)

    def cleanUp(self):
        ui.showContent()
        ui.task_label_box.hide()
        ui.book_options_box.show()
        ui.hidden_engines_box.clear()
        ui.web_engine.setInterceptor(None)

    def restart(self):
        self.cleanUp()
        QTimer.singleShot(0, startDownloadBooks)

    def close(self):
        self.cleanUp()
        QTimer.singleShot(0, close)

    def urlInterceptor(self, url):
        url = str(url.toString())
        url_part = url.replace(G.OCEANOFPDF_URL, "").lower()

        if self.locked:
            ui.status.setText("Please Wait...")
            return False

        if "pdf-" not in url_part and "epub-" not in url_part:
            return True

        if "epub-" not in url_part:
            ui.status.setText("EPUB Not Available! - Waiting For User Input...")
            return False

        if checkBookExists(v.books, "oceanofpdf_url", url):
            ui.status.setText("Already Downloaded! - Waiting For User Input...")
            return False

        self.locked = True
        self.queueDownload(url)
        return False

    def queueDownload(self, url):
        ui.status.setText("EPUB Available, Fetching...")
        ui.continue_btn.hide()


def close():
    v.download_worker = None
    v.process_worker = None
    v.upload_worker = None

    ui.book_list_box.show()
    ui.web_engine.hide()
    ui.task_btns_box.show()


def getSourceFiles():
    files = [f for f in os.listdir(os.getcwd()) if f.endswith(".epub")]

    for file in files:
        book = Book()
        book.getFileData(os.path.join(os.getcwd(), file))
        if book not in v.books:
            book.list_item = ui.BookItem(ui, book)
            v.books.append(book)


def getUserFiles():
    files, _ = QFileDialog.getOpenFileNames(None, "Select Files", "", "EPUB Files (*.epub)")

    for file in files:
        book = Book()
        book.getFileData(file)
        if book not in v.books:
            book.list_item = ui.BookItem(ui, book)
            ui.book_list_box.add(book.list_item)
            v.books.append(book)


def clearAllFiles():
    v.books = []


def startDownloadBooks():
    v.download_worker = Downloads()


def startProcessBooks(books=False):
    v.download_worker = None
    # v.process_worker = Process(books)


def startUploadBooks(books=False):
    v.upload_worker = None
    # v.upload_worker = Upload(books)


if __name__ == "__main__":
    v = G()
    app = QApplication(sys.argv)
    ui = UI()

    v.download_worker = None
    v.process_worker = None
    v.upload_worker = None

    ui.download_task_btn.click(startDownloadBooks)
    ui.process_task_btn.click(startProcessBooks)
    ui.upload_task_btn.click(startUploadBooks)

    ui.select_downloads_btn.click(getSourceFiles)
    ui.select_others_btn.click(getUserFiles)
    ui.clear_all_btn.click(clearAllFiles)

    sys.exit(app.exec())
