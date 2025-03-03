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

        ui.nav_btn_1.setText("Done")
        ui.nav_btn_1.click(self.close)

        ui.web_engine.show()
        ui.web_engine.setInterceptor(self.urlInterceptor)
        ui.web_engine.setUrl(G.OCEANOFPDF_URL)

    def cleanUp(self):
        ui.showContent()
        ui.hidden_engines_box.clear()
        ui.web_engine.setInterceptor(None)
        incomplete_books = []
        for book in G.books:
            if book.download_engine is not None or book.file_path is None:
                incomplete_books.append(book)

        for book in incomplete_books:
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
            ui.status.setText(
                "EPUB Not Available! - Waiting For User Input..."
            )
            return False

        if self.checkBookAlreadyDownloaded(url):
            ui.status.setText(
                "Already Downloaded! - Waiting For User Input..."
            )
            return False

        self.queueDownload(url)
        return False

    def checkBookAlreadyDownloaded(self, url):
        url = url.split("/")[-2]
        for book in G.books:
            if book.oceanofpdf_url is not None:
                if book.oceanofpdf_url.split("/")[-2] == url:
                    return True

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
        while (
            self.current_download_count < self.MAX_DOWNLOADS
            and self.download_queue
        ):
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
        file_name = os.path.basename(
            download.suggestedFileName().replace("/OceanofPDF.com/", "")
        )
        file_path = os.path.join(os.getcwd(), file_name)
        download.setDownloadFileName(file_path)
        download.accept()
        book = next(
            (
                b
                for b in G.books
                if b.download_engine == download.page().view()
            ),
            None,
        )
        book.list_item.progress_bar.config(text="Downloading")
        book.download = download
        book.file_name = file_name
        book.file_path = file_path
        book.download.downloadProgress.connect(
            book.list_item.progress_bar.updateProgress
        )
        book.download.finished.connect(lambda: self.downloadComplete(book))
        ui.updateUIParts()

    def downloadComplete(self, book):
        if book:
            book.getFileData(book.file_path)
            ui.updateUIParts()
        book.download_engine.delete()
        book.download_engine = None
        self.current_download_count -= 1
        self.processQueue()


class Process:
    def __init__(self):
        self.show_select = False
        self.setupUI()
        ui.updateUIParts()
        QTimer.singleShot(50, self.cleanBooks)

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
        for book in G.books:
            book.list_item.setTheme()
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
        ui.status.setText("Cleaning Books...")
        for book in G.books:
            if book is None:
                continue
            book_file = epubfile.Epub(book.file_path)
            book_pages = len(book_file.get_texts())
            book.list_item.progress_bar.config(value=0, text="Cleaning Pages")
            book.list_item.progress_bar.show()

            for index, page in enumerate(book_file.get_texts()):
                soup = book_file.read_file(page)
                soup = re.sub(G.STRING_TO_REMOVE, "", soup)
                book_file.write_file(page, soup)
                book.list_item.progress_bar.updateProgress(
                    index + 1, book_pages
                )

            book_file.save(book.file_path)
            book.list_item.progress_bar.hide()

        self.searchBook()

    def searchBook(self):
        ui.status.setText("Searching For Book Metadata...")
        G.setDeleteBtns(self.searchBook)
        ui.web_engine.show()
        ui.web_engine.loaded(ui.updateUIParts)
        ui.nav_btn_1.setText("Select")
        ui.nav_btn_1.click(
            lambda: ui.web_engine.page().toHtml(self.selectBook)
        )
        self.checkRequeue()
        for book in G.books:
            if not book.meta_updated:
                ui.nav_btn_2.setText("Skip")
                ui.nav_btn_2.click(
                    lambda: ui.confirmAction(
                        "Skip File - " + book.title,
                        "Are you sure you want to skip searching for this books details?",
                        action_true=lambda: (
                            book.metaSearchSkiped(),
                            self.searchBook(),
                        ),
                        warn_text=True,
                        warn_true=True,
                        image=book.cover,
                    )
                )
                ui.web_engine.setInterceptor(self.urlInterceptor)
                ui.web_engine.setUrl(
                    G.GOODREADS_URL
                    + "search?q="
                    + book.title.replace(" ", "+")
                    + "+"
                    + book.author.replace(" ", "+")
                )
                book.list_item.setTheme("highlight")
                ui.updateUIParts()
                return
        QTimer.singleShot(100, self.close)

    def urlInterceptor(self, url):
        url = str(url.toString())
        if not url.startswith(G.GOODREADS_URL):
            return False
        url_path = url.replace(G.GOODREADS_URL, "")
        if url_path.startswith("book/show/"):
            self.show_select = True
        else:
            self.show_select = False

        return True

    def selectBook(self, html):
        ui.status.setText("Scrapping Book Metadata...")
        self.show_select = False
        for book in G.books:
            if book.meta_updated:
                continue
            book.getGoodreadsData(
                html,
                lambda: ui.confirmAction(
                    "Original Cover Image",
                    "Are you happy with this cover image?",
                    self.completeBook,
                    lambda: self.selectCover(book.goodreads_cover),
                    image=book.cover,
                ),
            )
            return

    def selectCover(self, image=None, accept=None):
        ui.status.setText("Confirming Cover Image...")
        for book in G.books:
            if book.meta_updated:
                continue

            if book.cover_id is None:
                self.completeBook()
                return

            if accept is None:
                ui.confirmAction(
                    "Confirm Cover Image",
                    "Are you happy with this cover image?",
                    lambda: self.completeBook(image),
                    lambda: self.selectCover(accept=False),
                    image=image,
                )
                return

            if accept:
                ui.web_engine.setContextCall()
                self.completeBook(image)
                return

            ui.web_engine.setContextCall(self.selectCover)
            ui.web_engine.setInterceptor()
            ui.web_engine.loadedDone()
            ui.web_engine.setUrl(
                G.IMAGE_PROVIDER_URL
                + book.title.replace(" ", "+")
                + "+"
                + book.author.replace(" ", "+")
            )
            ui.nav_btn_1.setText("EPUB Cover")
            ui.nav_btn_1.click(lambda: self.selectCover(book.cover))
            ui.nav_btn_1.setText("Goodreads Cover")
            ui.nav_btn_1.click(lambda: self.selectCover(book.goodreads_cover))
            return

    def completeBook(self, image=None):
        ui.status.setText("Finalising book...")
        for book in G.books:
            if book.meta_updated:
                continue

            new_file_name = (
                book.title
                if book.title is not None
                else book.file_name.replace(".epub", "")
            )
            new_file_name += (
                f" - {book.author}" if book.author is not None else ""
            )
            new_file_path = os.path.join(os.getcwd(), new_file_name + ".epub")

            try:
                os.rename(book.file_path, new_file_path)
                book.file_path = new_file_path
                book.file_name = new_file_name
            except Exception as e:
                print(f"Error renaming file: {e}")

            if image is not None:
                book.cover = image
            book.saveCover()
            book.meta_updated = True
            book.list_item.setTheme()
            break
        ui.updateUIParts()
        self.searchBook()

    def checkRequeue(self):
        for book in G.books:
            if book.requeue:
                book.requeue = False
                book.meta_updated = False


def close():
    G.download_worker = None
    G.process_worker = None
    G.upload_worker = None

    ui.updateUIParts()


def getSourceFiles():
    files = [
        os.path.join(os.getcwd(), f)
        for f in os.listdir(os.getcwd())
        if f.endswith(".epub")
    ]
    collectFiles(files)


def getUserFiles():
    files, _ = QFileDialog.getOpenFileNames(
        None, "Select Files", "", "EPUB Files (*.epub)"
    )
    collectFiles(files)


def collectFiles(files):
    for file in files:
        book = Book(file)
        if not book.is_epub:
            continue
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
