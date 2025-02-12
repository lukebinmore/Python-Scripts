import os
import ebookmeta
import epubfile


class Book:
    def __init__(self, file_path=None):
        self.title = None
        self.author = None
        self.series = None
        self.series_index = None
        self.cover = None
        self.cover_id = None
        self.file_name = None
        self.file_path = None
        self.oceanofpdf_url = None
        self.list_item = None
        self.book_lists = []
        self.download = None

        if file_path is not None:
            self.getFileData(file_path)

    def __eq__(self, other):
        return isinstance(other, Book) and self.file_path == other.file_path

    def getFileData(self, file_path):
        self.file_path = os.path.normpath(file_path)
        self.file_name = os.path.basename(self.file_path)

        try:
            meta = ebookmeta.get_metadata(self.file_path)
            book = epubfile.Epub(self.file_path)

            self.title = meta.title.split("{")[0].split(":")[0]
            self.author = meta.author_list_to_string()
            self.series = meta.series or None
            self.series_index = meta.series_index or None

            self.cover_id = self.getCoverID(book)
            if self.cover_id is not None:
                self.cover = book.read_file(self.cover_id)

        except Exception as e:
            print(f"Error loading metadata: {e}")

    def getCoverID(self, book):
        false_positives = ["images/cover.png"]
        possible_tags = ["coverimagestandard", "cover.png", "cover-image", "cover"]

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

    def saveBook(self):
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

    def deleteBook(self, delete_file=False):
        for list in self.book_lists:
            if self in list:
                list.remove(self)

        if delete_file:
            try:
                os.remove(self.file_path)
            except FileNotFoundError:
                pass
