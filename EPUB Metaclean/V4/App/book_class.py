import os
import ebookmeta
import epubfile
from helper_functions import resizeCoverImage
from bs4 import XMLParsedAsHTMLWarning, BeautifulSoup
import warnings
import requests

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class Book:
    def __init__(self, file_path=None):
        self.is_epub = True
        self.title = None
        self.author = None
        self.series = None
        self.series_index = None
        self.cover = None
        self.cover_id = None
        self.cover_url = None
        self.possible_cover = None
        self.file_name = None
        self.file_path = None
        self.oceanofpdf_url = None
        self.list_item = None
        self.book_lists = []
        self.download = None
        self.download_engine = None
        self.cleaned = False
        self.meta_updated = False
        self.del_action = None
        self.requeue = False

        if file_path is not None:
            self.getFileData(file_path)

    def __eq__(self, other):
        if not isinstance(other, Book):
            return False
        if self.file_path is not None and other.file_path is not None:
            return self.file_path == other.file_path
        return self.title == other.title

    def getFileData(self, file_path):
        self.file_path = os.path.normpath(file_path)
        self.file_name = os.path.basename(self.file_path)

        if not os.path.exists(self.file_path):
            print("Testing")
            return

        try:
            meta = ebookmeta.get_metadata(self.file_path)
            book = epubfile.Epub(self.file_path)

            self.title = meta.title.split("{")[0].split(":")[0]
            self.author = meta.author_list_to_string()
            self.series = meta.series or None
            self.series_index = meta.series_index or None

            self.cover_id = self.getCoverID(book)
            if self.cover_id is not None:
                self.cover = resizeCoverImage(book.read_file(self.cover_id))

            if self.title is None:
                self.title = self.file_name

        except Exception as e:
            print(f"Error loading metadata: {e}")
            self.is_epub = False

    def getCoverID(self, book):
        false_positives = ["images/cover.png"]
        possible_tags = [
            "coverimagestandard",
            "cover.png",
            "cover-image",
            "cover",
        ]

        try:
            cover_id = book.get_cover_image()
            if cover_id and cover_id not in false_positives:
                return cover_id
        except Exception:
            pass

        for tag in possible_tags:
            try:
                if book.get_manifest_item(tag):
                    return tag
            except Exception:
                continue

        return None

    def getGoodreadsData(self, html, finished_action=None):
        total_steps = 8
        self.list_item.progress_bar.config(value=0, text="Scrapping Data...")
        self.list_item.progress_bar.show()

        soup = BeautifulSoup(html, "html.parser")
        self.list_item.progress_bar.updateProgress(
            1, total_steps, "Scraping Title..."
        )

        self.title = soup.select(".Text__title1")[0].text.strip()
        self.list_item.updateData()
        self.list_item.progress_bar.updateProgress(
            2, total_steps, "Scraping Author..."
        )

        self.author = soup.select(".ContributorLink__name")[0].text.strip()
        self.list_item.updateData()
        self.list_item.progress_bar.updateProgress(
            3, total_steps, "Scraping Series..."
        )

        series_text = soup.select_one(
            'a[href^="https://www.goodreads.com/series"]'
        )
        if series_text:
            series_text = series_text.get_text(strip=True)
            series_text = series_text.split("#")
            self.series = series_text[0].strip()
            self.list_item.updateData()
            if len(series_text) > 1:
                self.list_item.progress_bar.updateProgress(
                    4, total_steps, "Scraping Series Index..."
                )
                self.series_index = series_text[1].strip()
                self.list_item.updateData()

        self.list_item.progress_bar.updateProgress(
            5, total_steps, "Saving Metadata..."
        )
        self.saveMetadata()

        if self.cover_id is not None:
            self.list_item.progress_bar.updateProgress(
                6, total_steps, "Scraping Cover Url..."
            )

            self.cover_url = soup.select(".BookCover__image")[0].select("img")[
                0
            ]["src"]
            self.list_item.progress_bar.updateProgress(
                7, total_steps, "Downloading Cover..."
            )

            self.possible_cover = resizeCoverImage(
                requests.get(self.cover_url, stream=True).content
            )

        self.list_item.progress_bar.updateProgress(
            total_steps, total_steps, "Finished"
        )
        self.list_item.progress_bar.hide()
        if finished_action is not None:
            finished_action()

    def saveMetadata(self):
        if not self.file_path:
            raise ValueError("No file path set for the book.")

        meta = ebookmeta.get_metadata(self.file_path)

        meta.title = self.title
        meta.set_author_list_from_string(self.author)
        meta.series = self.series
        meta.series_index = self.series_index

        try:
            ebookmeta.set_metadata(self.file_path, meta)

            if self.cover_id is not None:
                book = epubfile.Epub(self.file_path)
                book.write_file(self.cover_id, self.cover)
                book.save(self.file_path)
        except Exception as e:
            print(f"Error saving metadata: {e}")

    def saveCover(self):
        try:
            if self.cover_id is not None:
                book = epubfile.Epub(self.file_path)
                book.write_file(self.cover_id, self.cover)
                book.save(self.file_path)
        except Exception as e:
            print(f"Error saving metadata: {e}")

    def deleteBook(self, delete_file=False):
        for list in self.book_lists:
            if self in list:
                list.remove(self)

        if self.download_engine is not None:
            self.download_engine.delete()

        if self.download:
            self.download.cancel()

        if delete_file and self.file_path is not None:
            try:
                os.remove(self.file_path)
            except FileNotFoundError:
                pass

        if self.list_item is not None:
            self.list_item.delete()

        if self.del_action is not None:
            self.del_action()

    def metaSearchSkiped(self):
        self.meta_updated = True
        self.list_item.setTheme()
