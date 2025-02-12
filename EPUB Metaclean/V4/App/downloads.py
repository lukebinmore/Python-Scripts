class Downloads:
    

    

    

    

    


class Downloads:
    def queueDownload(self, url):
        ui.status.setText("EPUB Available, Fetching...")
        ui.continue_btn_box.hide()
        ui.book_list_box.show()

        book = Book()
        self.books.append(book)
        book.book_lists.append(self.books)

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
        book.book_list_item = ui.BookItem(ui, book)
        book.book_list_item.item_progress_bar.config(text="Downloading")
        book.book_list_item.item_progress_bar.show()

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
        self.download_queue += 1

    def openBookPage(self, download_engine):
        ui.status.setText("Adding Book To Download Queue...")
        js_code = """
        var element = document.querySelector("input[type='image'][src^='https://media.oceanofpdf.com/epub-button']");
        if (element) {
            element.click();
        }
        """
        download_engine.page().runJavaScript(js_code)
        self.locked = False

    def handleDownload(self, download):
        file_name = os.path.basename(download.suggestedFileName().replace("/OceanofPDF.com/", ""))
        file_path = os.path.join(os.getcwd(), file_name)
        download.setDownloadFileName(file_path)
        download.accept()
        book = self.download_map.get(download.page().view())
        book.download = download

        if book is None:
            ui.status.setText("Error: Could not find book in download map.")
            return

        book.file_name = file_name
        book.file_path = file_path

        book.download.downloadProgress.connect(book.book_list_item.item_progress_bar.updateProgress)
        book.download.finished.connect(lambda: self.downloadComplete(download))
        ui.status.setText("Waiting For User Input...")

    def downloadComplete(self, download):
        download_engine = download.page().view()
        book = self.download_map.pop(download_engine, None)

        if book:
            book.getFileData(book.file_path)
        download_engine.delete()

        self.download_count += 1
        if self.download_count >= self.download_queue:
            ui.status.setText("Waiting For User Input...")
            ui.continue_btn_box.show()

    def startProcessBooks(self):
        self.cleanUp()
        QTimer.singleShot(0, lambda: startProcessBooks(self.books))
