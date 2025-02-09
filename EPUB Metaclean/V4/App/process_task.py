class Process:
    def __init__(self, books):
        self.books = []
        self.curr_index = -1

        if not books == False:
            self.books = books
            for book in self.books:
                book.getFileData()

        ui.restart_btn.click(
            lambda: ui.confirmAction(
                "Restarting Processing Task!",
                "Are you sure you would like to restart the process task?",
                self.restart,
                warn_text=True,
                warn_true=True,
            )
        )

        ui.close_btn.click(
            lambda: ui.confirmAction(
                "Cancelling Process Task!",
                "Are you sure you would like to cancel the process task?",
                self.close,
                warn_text=True,
                warn_true=True,
            )
        )

        ui.select_downloads_btn.click(self.getSourceFiles)
        ui.select_others_btn.click(self.getUserFiles)
        ui.clear_selections_btn.click(
            lambda: ui.confirmAction(
                "Clear All Files",
                "Are you sure you would like to clear all files from the list?\nNOTE: The source files will NOT be deleted!",
                self.clearAllFiles,
                warn_text=True,
                warn_true=True,
            )
        )

        ui.continue_btn.click(self.cleanPages)
        ui.continue_btn.setText("Process Books")

        self.initBookSelection()

    def restart(self):
        ui.process_list_box.clear()
        startProcessBooks()

    def close(self):
        ui.process_list_box.clear()
        close()

    def checkSource(self):
        files = [f for f in os.listdir(os.getcwd()) if f.endswith(".epub")]

        if files:
            return True

        return False

    def initBookSelection(self):
        ui.showListPage("Processing Books")

        if len(self.books) > 0:
            self.books.sort(key=lambda book: book.title.lower())

        for book in self.books:
            book.initListItem(self.books, action=lambda: self.initBookSelection())

        ui.select_downloads_btn.hide()
        ui.select_downloads_btn.show() if self.checkSource() else None
        ui.clear_selections_btn.hide()

        if len(self.books) > 0:
            ui.clear_selections_btn.show()
            ui.continue_btn_box.show()

    def getSourceFiles(self):
        files = [f for f in os.listdir(os.getcwd()) if f.endswith(".epub")]

        for file in files:
            book = Book()
            book.getFileData(os.path.join(os.getcwd(), file))
            if book not in self.books:
                self.books.append(book)

        self.confirmSourceFiles(0)

    def confirmSourceFiles(self, index):
        if index == len(self.books):
            self.initBookSelection()
            return

        base_text = "Would you like to process this book?\n" + self.books[index].file_name
        if self.books[index].cover_id is None:
            base_text = base_text + "\n\nWARNING: Cannot update cover image due to file error!"

        ui.confirmAction(
            "Process This Book?",
            base_text,
            lambda: self.confirmSourceFiles(index + 1),
            lambda: self.books[index].deleteBook(self.books, action=lambda: self.confirmSourceFiles(index)),
        )

    def getUserFiles(self):
        files, _ = QFileDialog.getOpenFileNames(None, "Select Files", "", "EPUB FIles (*.epub)")

        for file in files:
            book = Book()
            book.getFileData(file)
            if book not in self.books:
                self.books.append(book)

        self.initBookSelection()

    def clearAllFiles(self):
        self.books = []
        self.initBookSelection()

    def cleanPages(self):
        ui.showTaskPage("Processing Books", status="Cleaning Books...")

        for book in self.books:
            ui.notice_label_title.setText(f"Cleaning {book.title}...")

            book_file = epubfile.Epub(book.file_path)

            book_pages = len(book_file.get_texts())
            ui.updateProgressBar(0, book_pages, True)

            for index, page in enumerate(book_file.get_texts(), start=1):
                ui.notice_label.setText(f"Page {index} Of {book_pages}")
                soup = book_file.read_file(page)
                soup = re.sub(v.STRING_TO_REMOVE, "", soup, flags=re.IGNORECASE)
                book_file.write_file(page, soup)
                ui.updateProgressBar(1)

            book_file.save(book.file_path)

            ui.updateProgressBar(1)

        self.searchBook()

    def urlInterceptor(self, url):
        url = str(url.toString())

        if url.startswith(v.GOODREADS_URL):
            url_path = url.replace(v.GOODREADS_URL, "")

            if url_path.startswith("book/show/"):
                ui.web_engine.loaded(ui.select_btn.show)
            else:
                ui.web_engine.loadedDone()
                ui.select_btn.hide()

        return True

    def searchBook(self):
        self.curr_index += 1

        if self.curr_index == len(self.books):
            self.curr_index = -1
            self.saveBooks()
            return

        ui.select_btn.click(lambda: ui.web_engine.page().toHtml(self.selectBook))

        ui.skip_btn.setText("Skip")
        ui.skip_btn.click(
            lambda: ui.confirmAction(
                "Skip File",
                "Are you sure you want to skip searching for this books details?",
                action_true=self.searchBook,
                warn_text=True,
                warn_true=True,
            )
        )

        replacements = [
            f"_{v.STRING_TO_REMOVE}_",
            "-",
            "_",
            "(",
            ")",
            ".epub",
            " ",
        ]
        query = self.books[self.curr_index].title

        for part in replacements:
            query = query.replace(part, "+")

        ui.showBrowserPage(
            "Processing Books",
            url=f"{v.GOODREADS_URL}search?q={query}",
            interceptor=self.urlInterceptor,
        )

        ui.current_file_box.show()
        ui.current_file_label.setText(f"Searching For: {self.books[self.curr_index].title}")

        ui.nav_btns_box.show()

    def selectBook(self, html):
        ui.showTaskPage("Processing Books", status="Pulling Book Data From Page...")

        ui.updateProgressBar(0, 7, True)

        book = self.books[self.curr_index]
        soup = BeautifulSoup(html, "html.parser")

        ui.notice_label_title.setText("Fetching Data:")

        book.title = soup.select(".Text__title1")[0].text.strip()
        ui.notice_label.setText(f"Title: {book.title}")
        ui.updateProgressBar(1)

        book.author = soup.select(".ContributorLink__name")[0].text.strip()
        ui.notice_label.setText(f"Author: {book.author}")
        ui.updateProgressBar(1)

        series_link = soup.select_one('a[href^="https://www.goodreads.com/series"]')
        ui.updateProgressBar(1)

        if series_link:
            book.series = series_link.contents[0].strip()
            book.series_index = series_link.contents[1].strip()
            ui.notice_label.setText(f"Series: {book.series} #{book.series_index}")

        ui.updateProgressBar(1)

        if book.cover_id is None:
            self.books[self.curr_index] = book
            ui.updateProgressBar(3)
            self.searchBook()
            return

        book.cover_url = soup.select(".BookCover__image")[0].select("img")[0]["src"]
        ui.notice_label.setText(f"Cover URL: {book.cover_url}")
        ui.updateProgressBar(1)

        ui.notice_label.setText(f"Cover: Downloading...")
        book.cover = requests.get(book.cover_url, stream=True).content
        ui.updateProgressBar(1)

        self.books[self.curr_index] = book
        ui.updateProgressBar(1)

        if self.curr_index == 0:
            ui.confirmAction(
                "Cover Instructions",
                "To select a cover image, find an image you like and right click it. If it can be used, there will be a 'Select' option.",
                lambda: self.selectCover(self.books[self.curr_index].cover),
                info=True,
            )
        else:
            self.selectCover(self.books[self.curr_index].cover)

    def selectCover(self, img_data, accepted=None):
        image = resizeCoverImage(img_data)

        if accepted is None:
            ui.confirmAction(
                "Check Cover Image",
                "Are you happy with this cover image?\n"
                + "NOTE: You can search Google Images for a different cover image if you select no.\n"
                + "If the menu doesn't appear, the image is not the correct format.",
                lambda: self.selectCover(image, True),
                lambda: self.selectCover(image, False),
                image=image,
            )
            return

        if accepted:
            self.books[self.curr_index].cover = image
            ui.web_engine.setContextCall()
            self.searchBook()
            return

        ui.web_engine.setContextCall(self.selectCover)

        ui.showBrowserPage(
            "Processing Book",
            url=f"{v.IMAGE_PROVIDER_URL}{self.books[self.curr_index].title}",
        )

        ui.select_btn.hide()
        ui.skip_btn.setText("Goodreads")
        ui.skip_btn.click(lambda: self.selectCover(self.books[self.curr_index].cover))
        ui.nav_btns_box.show()

    def saveBooks(self):
        ui.showTaskPage("Processing Books", status="Saving Books...")
        ui.updateProgressBar(0, len(self.books) * 9, True)

        for book in self.books:
            book.saveBook()

        ui.process_list_box.clear()

        ui.confirmAction(
            "Upload Books",
            "Would you like to upload these books to Play Books?",
            lambda: startUploadBooks(self.books),
            close,
        )
