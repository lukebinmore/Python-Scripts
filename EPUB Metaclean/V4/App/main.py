import sys
from globals import Globals as G
from ui import UI
from book_class import Book
from helper_functions import *
from qt_overrides import WebEngineView
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QTimer

from PyQt5.QtWidgets import *
from functools import partial


class Downloads:
    def __init__(self):
        self.download_queue = 0
        self.download_count = 0
        self.books = []
        self.download_map = {}
        self.locked = False
        self.retry_attempts = {}
        self.MAX_RETRIES = 3

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
                "Are you sure you would like to cancel the download task?",
                self.close,
                warn_text=True,
                warn_true=True,
            )
        )

        ui.continue_btn.setText("Process Downloads")
        ui.continue_btn.click(
            lambda: ui.confirmAction(
                "Process Books", "Are you sure you want to process these books?", self.startProcessBooks
            )
        )

        ui.showBrowserPage("Downloading New Books", G.OCEANOFPDF_URL, interceptor=self.urlInterceptor)

    def cleanUp(self):
        ui.hidden_engines_box.clear()
        ui.web_engine.setInterceptor(None)
        self.download_queue = 0
        self.download_count = 0
        self.books.clear()
        self.download_map.clear()
        self.locked = False

    def restart(self):
        self.cleanUp()
        QTimer.singleShot(0, startDownloadBooks)

    def close(self):
        self.cleanUp()
        QTimer.singleShot(0, close)

    def urlInterceptor(self, url):
        url = str(url.toString())
        url_part = url.replace(G.OCEANOFPDF_URL, "")

        if self.locked:
            ui.status.setText("Please Wait...")
            return False

        if "pdf-" not in url_part or "epub-" not in url_part:
            return True

        if "epub-" not in url_part:
            ui.status.setText("EPUB Not Available! - Waiting For User Input...")
            return False

        if checkBookExists(self.books, "oceanofpdf_url", url):
            ui.status.setText("Already Downloaded! - Waiting For User Input...")
            return False

        self.locked = True
        self.queueDownload(url)
        return False

    def queueDownload(self, url):
        ui.status.setText("EPUB Available, Fetching...")
        ui.continue_btn_box.hide()
        ui.book_list_box.show()

        book = Book()
        self.books.append(book)
        book.book_lists.append(self.books)

        book.oceanofpdf_url = url
        book.title = (
            url.lower()
            .split("/")[-2]
            .replace("pdf-", "")
            .replace("epub-", "")
            .replace("download", "")
            .replace("-", " ")
            .title()
        )
        book.book_list_item = ui.BookItem(ui, book)
        book.book_list_item.item_progress_bar.config(text="Downloading")
        book.book_list_item.item_progress_bar.show()

        download_engine = WebEngineView(ui.hidden_engines_box)

        new_window = QMainWindow()
        new_window.setGeometry(100, 100, 600, 600)
        new_window.setCentralWidget(download_engine)
        self.windows.append(new_window)
        new_window.show()

        self.download_map[download_engine] = book

        download_engine.downloadReq(self.handleDownload)
        download_engine.loaded(lambda: self.openBookPage(download_engine))
        download_engine.setUrl(url)
        self.download_queue += 1

    def openBookPage(self, download_engine):
        ui.status.setText("Adding Book To Download Queue...")
        js_code = """
        var element = document.querySelector("input[type='image'][src^='https://media.oceanofpdf.com/epub-button']");
        if (element) {
            element.click();
        }
        """
        download_engine.page().runJavaScript(js_code)
        self.locked = False

    def handleDownload(self, download):
        file_name = os.path.basename(download.suggestedFileName().replace("/OceanofPDF.com/", ""))
        file_path = os.path.join(os.getcwd(), file_name)
        download.setDownloadFileName(file_path)
        download.accept()
        book = self.download_map.get(download.page().view())

        if book is None:
            ui.status.setText("Error: Could not find book in download map.")
            return

        book.file_name = file_name
        book.file_path = file_path
        download.downloadProgress.connect(book.book_list_item.item_progress_bar.updateProgress)
        download.finished.connect(lambda: self.downloadComplete(download))
        ui.status.setText("Waiting For User Input...")

    def downloadComplete(self, download):
        download_engine = download.page().view()
        book = self.download_map.pop(download_engine, None)

        if book:
            book.getFileData(book.file_path)
        download_engine.delete()

        self.download_count += 1
        if self.download_count >= self.download_queue:
            ui.status.setText("Waiting For User Input...")
            ui.continue_btn_box.show()

    def startProcessBooks(self):
        self.cleanUp()
        QTimer.singleShot(0, lambda: startProcessBooks(self.books))


def close():
    v.download_worker = None
    v.process_worker = None
    v.upload_worker = None

    ui.showHome()


def startDownloadBooks():
    v.download_worker = Downloads()


def startProcessBooks(books=False):
    v.download_worker = None
    # v.process_worker = Process(books)


def startUploadBooks(books=False):
    v.upload_worker = None
    # v.upload_worker = Upload(books)


if __name__ == "__main__":
    v = G
    app = QApplication(sys.argv)
    ui = UI()

    v.download_worker = None
    v.process_worker = None
    v.upload_worker = None

    ui.download_task_btn.click(startDownloadBooks)
    ui.process_task_btn.click(startProcessBooks)
    ui.upload_task_btn.click(startUploadBooks)

    ui.task_btns_box.show()

    sys.exit(app.exec())
