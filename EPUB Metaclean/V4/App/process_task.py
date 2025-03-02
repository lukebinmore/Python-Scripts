    def checkSource(self):
        files = [f for f in os.listdir(os.getcwd()) if f.endswith(".epub")]

        if files:
            return True

        return False

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
