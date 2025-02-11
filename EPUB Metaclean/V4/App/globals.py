from PyQt5.QtWidgets import QSizePolicy


class Globals:
    TITLE = "EPUB Metaclean V4"
    ICON = "icon.ico"
    MINIMUM_SIZE = 460, 460
    STYLES_FILE = "styles.qss"

    DEFAULT_MARGINS = 3, 3, 3, 3
    OCEANOFPDF_URL = "https://oceanofpdf.com/"
    STRING_TO_REMOVE = "OceanofPDF.com"
    GOODREADS_URL = "https://www.goodreads.com/"
    IMAGE_PROVIDER_URL = "https://www.google.com/search?tbm=isch&q="
    PLAY_BOOKS = "https://play.google.com/books"

    PREFERRED = QSizePolicy.Preferred
    EXPANDING = QSizePolicy.Expanding
    MINIMUM = QSizePolicy.Minimum
    FIXED = QSizePolicy.Fixed

    STYLE_VARIABLES = {
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
        "border_radius": "10px",
    }

    download_worker = None
    process_worker = None
    upload_worker = None
