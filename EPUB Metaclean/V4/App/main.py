import sys
from globals import G
from ui import UI
from book_class import Book
from helper_functions import *
from qt_overrides import WebEngineView
from PyQt5.QtWidgets import QApplication, QFileDialog, QMainWindow
from PyQt5.QtCore import QTimer


class Downloads:
    def __init__(self):
        self.download_map = {}
        self.locked = False

        self.windows = []

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
        ui.done_btn.click(lambda: (ui.done_btn.hide(), self.close()))

        ui.web_engine.show()
        ui.web_engine.setInterceptor(self.urlInterceptor)
        ui.web_engine.setUrl(G.OCEANOFPDF_URL)

    def cleanUp(self):
        ui.showContent()
        ui.hidden_engines_box.clear()
        ui.web_engine.setInterceptor(None)

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

        if self.locked:
            ui.status.setText("Please Wait...")
            return False

        if "pdf-" not in url_part and "epub-" not in url_part:
            return True

        if "epub-" not in url_part:
            ui.status.setText("EPUB Not Available! - Waiting For User Input...")
            return False

        if checkBookExists(G.books, "oceanofpdf_url", url):
            ui.status.setText("Already Downloaded! - Waiting For User Input...")
            return False

        self.locked = True
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
        book.list_item.progress_bar.config(text="Downloading")
        book.list_item.progress_bar.show()
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
        ui.updateUIParts()

    def openBookPage(self, download_engine):
        js_code = """
        var element = document.querySelector("input[type='image'][src^='https://media.oceanofpdf.com/epub-button']");
        if (element) {
            element.click();
        }
        """
        download_engine.page().runJavaScript(js_code)
        self.locked = False

    def handleDownload(self, download):
        ui.status.setText("Waiting For User Input...")
        file_name = os.path.basename(download.suggestedFileName().replace("/OceanofPDF.com/", ""))
        file_path = os.path.join(os.getcwd(), file_name)
        download.setDownloadFileName(file_path)
        download.accept()
        book = self.download_map.get(download.page().view())
        book.download = download
        book.file_name = file_name
        book.file_path = file_path
        book.download.downloadProgress.connect(book.list_item.progress_bar.updateProgress)
        book.download.finished.connect(lambda: self.downloadComplete(download))
        book.list_item.updateData()
        ui.updateUIParts()

    def downloadComplete(self, download):
        download_engine = download.page().view()
        book = self.download_map.pop(download_engine, None)
        if book:
            book.getFileData(book.file_path)
            book.list_item.updateData()
            ui.updateUIParts()
        download_engine.delete()


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
    # G.process_worker = Process()


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
            lambda: (ui.showContent(), ui.updateUIParts(), clearAllFiles()),
            lambda: (ui.showContent(), ui.updateUIParts()),
            warn_text=True,
            warn_true=True,
        )
    )

    ui.updateUIParts()

    sys.exit(app.exec())
