import sys
from globals import Globals as G
from ui import UI
from book_class import Book
from helper_functions import *
from qt_overrides import WebEngineView
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer


class Downloads:
    def __init__(self):
        self.download_queue = 0
        self.download_count = 0
        self.books = []
        self.download_map = {}
        self.locked = False
        self.retry_attempts = {}
        self.MAX_RETRIES = 3

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

        ui.progress_bar.config(0, 0, "Downloading: %v / %m")

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

        if not url_part.startswith("authors/"):
            return True

        epub_available = url_part.split("/")[2].replace("pdf-", "")

        if not epub_available.startswith("epub"):
            ui.status.setText("EPUB Not Available!! - Waiting For User Input...")
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
        book = Book()
        book.oceanofpdf_url = url
        self.books.append(book)
        download_engine = WebEngineView(ui.hidden_engines_box)
        self.download_map[download_engine] = book
        self.retry_attempts[download_engine] = 0

        timeout_timer = QTimer()
        timeout_timer.setSingleShot(True)
        timeout_timer.timeout.connect(lambda: self.handleTimeout(download_engine))
        timeout_timer.start(15000)
        download_engine.timeout_timer = timeout_timer

        download_engine.downloadReq(self.handleDownload)
        download_engine.loaded(lambda: self.openBookPage(download_engine))
        download_engine.setUrl(url)
        self.download_queue += 1

    def handleTimeout(self, download_engine):
        if download_engine not in self.download_map:
            return

        retries = self.retry_attempts.get(download_engine, 0)
        if retries >= self.MAX_RETRIES:
            ui.status.setText("Download Failed! - Skipping")
            self.download_map.pop(download_engine, None)
            download_engine.delete()
            return

        ui.status.setText(f"Download Timed Out! Retrying ({retries + 1})/{self.MAX_RETRIES}...")
        self.retry_attempts[download_engine] += 1

        download_engine.reload()

    def openBookPage(self, download_engine):
        ui.status.setText("Adding Book To Download Queue...")
        download_engine.loadedDone()
        js_code = """
        var element = document.querySelector("input[type='image'][src^='https://media.oceanofpdf.com/epub-button']");
        if (element) {
            element.click();
        }
        """
        download_engine.page().runJavaScript(js_code)

    def handleDownload(self, download):
        file_name = os.path.basename(download.suggestedFileName().replace("/OceanofPDF.com/", ""))
        file_path = os.path.join(os.getcwd(), file_name)
        download.setDownloadFileName(file_path)
        download.accept()
        ui.progress_box.show()
        ui.progress_bar.config(range=self.download_queue)
        book = self.download_map.get(download.page().view())

        if book is None:
            ui.status.setText("Error: Could not find book in download map.")
            return

        book.file_name = file_name
        book.file_path = file_path
        download.finished.connect(lambda: self.downloadComplete(download))
        ui.status.setText("Waiting For User Input...")
        self.locked = False

    def downloadComplete(self, download):
        download_engine = download.page().view()
        book = self.download_map.pop(download_engine, None)
        if book:
            book.getFileData(book.file_path)
        download_engine.delete()

        ui.progress_bar.update()
        self.download_count += 1
        if self.download_count >= self.download_queue:
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
