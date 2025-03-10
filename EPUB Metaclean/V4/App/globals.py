from PyQt5.QtWidgets import QSizePolicy
import os


class Globals:
    def __init__(self):
        self.TITLE = "EPUB Metaclean V4"
        self.ICON = "icon.ico"
        self.MINIMUM_SIZE = 460, 460
        self.STYLES_FILE = "styles.qss"

        self.DEFAULT_MARGINS = 6, 6, 6, 6
        self.THUMBNAIL_SIZE = 80, 128
        self.OCEANOFPDF_URL = "https://oceanofpdf.com/"
        self.STRING_TO_REMOVE = "OceanofPDF.com"
        self.GOODREADS_URL = "https://www.goodreads.com/"
        self.IMAGE_PROVIDER_URL = "https://www.google.com/search?tbm=isch&q="
        self.PLAY_BOOKS = "https://play.google.com/books"
        self.DOWNLOAD_LOCATION = os.path.join(
            os.path.expanduser("~"), "Desktop", "Books"
        )

        self.PREFERRED = QSizePolicy.Preferred
        self.EXPANDING = QSizePolicy.Expanding
        self.MINIMUM = QSizePolicy.Minimum
        self.FIXED = QSizePolicy.Fixed
        self.MINIMUMEXPANDING = QSizePolicy.MinimumExpanding

        self.STYLE_VARIABLES = {
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
            "border_radius": "8",
        }

        self.download_worker = None
        self.process_worker = None
        self.upload_worker = None

        self.books = []

    def addBook(self, book):
        book.book_lists.append(self.books)
        self.books.append(book)
        self.books.sort(key=lambda b: b.title.lower() if b.title else "")
        return self.books.index(book)

    def setDeleteBtns(self, action=None):
        for book in self.books:
            book.del_action = action


G = Globals()
