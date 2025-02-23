import sys
import epubfile
import re
from globals import G
from ui import UI
from book_class import Book
from helper_functions import *
from qt_overrides import WebEngineView
from PyQt5.QtWidgets import QApplication, QFileDialog
from PyQt5.QtCore import QTimer


class Downloads:
    MAX_DOWNLOADS = 3

    def __init__(self):
        self.download_queue = []
        self.current_download_count = 0

        self.setupUI()
        ui.updateUIParts()

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

        ui.done_btn.setText("Done")
        ui.done_btn.click(self.close)

        ui.web_engine.show()
        ui.web_engine.setInterceptor(self.urlInterceptor)
        ui.web_engine.setUrl(G.OCEANOFPDF_URL)

    def cleanUp(self):
        ui.showContent()
        ui.hidden_engines_box.clear()
        ui.web_engine.setInterceptor(None)
        for book in G.books:
            if book.download_engine is not None:
                book.deleteBook()

    def restart(self):
        self.cleanUp()
        QTimer.singleShot(0, startDownloadBooks)

    def close(self):
        self.cleanUp()
        ui.web_engine.hide()
        QTimer.singleShot(0, close)

    def urlInterceptor(self, url):
        url = str(url.toString())
        url_part = url.replace(G.OCEANOFPDF_URL, "").lower()

        if "pdf-" not in url_part and "epub-" not in url_part:
            return True

        if "epub-" not in url_part:
            ui.status.setText("EPUB Not Available! - Waiting For User Input...")
            return False

        if checkBookExists(G.books, "oceanofpdf_url", url):
            ui.status.setText("Already Downloaded! - Waiting For User Input...")
            return False

        self.queueDownload(url)
        return False

    def queueDownload(self, url):
        ui.status.setText("EPUB Available, Fetching...")
        book = Book()
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
        insert_index = G.addBook(book)
        book.list_item = ui.BookItem(ui, book, insert_index)
        book.list_item.progress_bar.config(text="Queued")
        book.list_item.progress_bar.show()
        book.book_lists.append(self.download_queue)
        self.download_queue.append(book)
        self.processQueue()

    def processQueue(self):
        while self.current_download_count < self.MAX_DOWNLOADS and self.download_queue:
            book = self.download_queue.pop(0)
            self.current_download_count += 1
            self.startDownload(book)

    def startDownload(self, book):
        book.list_item.progress_bar.config(text="Starting Download")
        book.download_engine = WebEngineView(ui.hidden_engines_box)
        book.download_engine.downloadReq(self.handleDownload)
        book.download_engine.loaded(lambda: self.openBookPage(book))
        book.download_engine.setUrl(book.oceanofpdf_url)
        ui.updateUIParts()

    def openBookPage(self, book):
        js_code = """
        setTimeout(function() {
            try {
                var epubButton = document.querySelector("input[type='image'][src^='https://media.oceanofpdf.com/epub-button']");
                if (epubButton) {
                    epubButton.click();
                }
            } catch (error) {
                console.error("JavaScript Error:", error);
            }
        }, 500);
        """
        book.download_engine.page().runJavaScript(js_code, lambda result: None)

    def handleDownload(self, download):
        ui.status.setText("Waiting For User Input...")
        file_name = os.path.basename(download.suggestedFileName().replace("/OceanofPDF.com/", ""))
        file_path = os.path.join(os.getcwd(), file_name)
        download.setDownloadFileName(file_path)
        download.accept()
        book = next((b for b in G.books if b.download_engine == download.page().view()), None)
        book.list_item.progress_bar.config(text="Downloading")
        book.download = download
        book.file_name = file_name
        book.file_path = file_path
        book.download.downloadProgress.connect(book.list_item.progress_bar.updateProgress)
        book.download.finished.connect(lambda: self.downloadComplete(book))
        book.list_item.updateData()
        ui.updateUIParts()

    def downloadComplete(self, book):
        if book:
            book.getFileData(book.file_path)
            book.list_item.updateData()
            ui.updateUIParts()
        book.download_engine.delete()
        book.download_engine = None
        self.current_download_count -= 1
        self.processQueue()


class Process:
    def __init__(self):
        self.setupUI()
        ui.updateUIParts()
        self.cleanBooks()

    def setupUI(self):
        ui.restart_btn.click(
            lambda: ui.confirmAction(
                "Restarting Process Task!",
                "Are you sure you would like to restart the process task?",
                self.restart,
                warn_text=True,
                warn_true=True,
            )
        )

        ui.close_btn.click(
            lambda: ui.confirmAction(
                "Cancelling Process Task!",
                "Are you sure you would like to end the process task?",
                self.close,
                warn_text=True,
                warn_true=True,
            )
        )

    def cleanUp(self):
        ui.showContent()
        ui.hidden_engines_box.clear()
        ui.web_engine.setInterceptor(None)

    def restart(self):
        self.cleanUp()
        QTimer.singleShot(0, startProcessBooks)

    def close(self):
        self.cleanUp()
        ui.web_engine.hide()
        QTimer.singleShot(0, close)

    def cleanBooks(self):
        def cleanBook(book):
            book_file = epubfile.Epub(book.file_path)
            book_pages = len(book_file.get_texts())
            book.list_item.progress_bar.config(value=0, text="Cleaning Pages")
            book.list_item.progress_bar.show()

            for index, page in enumerate(book_file.get_texts()):
                soup = book_file.read_file(page)
                soup = re.sub(G.STRING_TO_REMOVE, "", soup)
                book_file.write_file(page, soup)
                book.list_item.progress_bar.updateProgress(index + 1, book_pages)

            book_file.save(book.file_path)
            book.list_item.progress_bar.hide()

        ui.status.setText("Cleaning Books...")
        for curr_book in G.books:
            QTimer.singleShot(50, lambda: cleanBook(curr_book))


def close():
    G.download_worker = None
    G.process_worker = None
    G.upload_worker = None

    ui.updateUIParts()


def getSourceFiles():
    files = [f for f in os.listdir(os.getcwd()) if f.endswith(".epub")]

    for file in files:
        book = Book(file)
        book.download = False
        if book not in G.books:
            insert_index = G.addBook(book)
            book.list_item = ui.BookItem(ui, book, insert_index)

    ui.updateUIParts()


def getUserFiles():
    files, _ = QFileDialog.getOpenFileNames(None, "Select Files", "", "EPUB Files (*.epub)")

    for file in files:
        book = Book(file)
        book.download = False
        if book not in G.books:
            insert_index = G.addBook(book)
            book.list_item = ui.BookItem(ui, book, insert_index)

    ui.updateUIParts()


def clearAllFiles():
    G.books = []
    ui.book_list_box.container.clear()


def startDownloadBooks():
    close()
    G.download_worker = Downloads()


def startProcessBooks():
    close()
    G.process_worker = Process()


def startUploadBooks():
    close()
    # G.upload_worker = Upload()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui = UI()

    G.download_worker = None
    G.process_worker = None
    G.upload_worker = None

    ui.download_task_btn.click(startDownloadBooks)
    ui.process_task_btn.click(startProcessBooks)
    ui.upload_task_btn.click(startUploadBooks)

    ui.select_downloads_btn.click(getSourceFiles)
    ui.select_others_btn.click(getUserFiles)
    ui.clear_all_btn.click(
        lambda: ui.confirmAction(
            "Clearing Books",
            "Are you sure you would like to clear all opened books?",
            lambda: (ui.updateUIParts(), clearAllFiles()),
            lambda: ui.updateUIParts(),
            warn_text=True,
            warn_true=True,
        )
    )

    ui.updateUIParts()

    sys.exit(app.exec())
