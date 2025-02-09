class Upload:
    def __init__(self, books):
        self.books = []

        if not books == False:
            self.books = books

        ui.restart_btn.click(
            lambda: ui.confirmAction(
                "Restarting Upload Task!",
                "Are you sure you would like to restart the upload task?",
                self.restart,
                warn_text=True,
                warn_true=True,
            )
        )

        ui.close_btn.click(
            lambda: ui.confirmAction(
                "Cancelling Upload Task!",
                "Are you sure you would like to cancel the upload task?",
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

        ui.continue_btn.click(self.startPlayBooksUpload)
        ui.continue_btn.setText("Upload Books")

        self.initBookSelection()

    def restart(self):
        ui.process_list_box.clear()
        startUploadBooks()

    def close(self):
        ui.process_list_box.clear()
        close()

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

        base_text = "Would you like to upload this book?\n" + self.books[index].file_name

        ui.confirmAction(
            "Upload This Book?",
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

    def checkSource(self):
        files = [f for f in os.listdir(os.getcwd()) if f.endswith(".epub")]

        if files:
            return True

        return False

    def initBookSelection(self):
        ui.showListPage("Uploading Books")

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

    def startPlayBooksUpload(self, upload_confirmed=False):
        ui.continue_btn_box.hide()

        if not upload_confirmed:
            ui.confirmAction(
                "Upload To Play Books?",
                "Would you like to upload these books to play books?",
                lambda: self.startPlayBooksUpload(True),
                self.close,
            )

        else:
            ui.web_engine.loaded(lambda: self.checkPlayBooksLogin())
            ui.showBrowserPage(
                "Uploading Books To Play Books",
                status="Uploading To Play Books...",
                url=v.PLAY_BOOKS,
            )
            ui.continue_btn.click(lambda: self.startPlayBooksUpload(True))
            ui.continue_btn.setText("I Have Logged In")

    def checkPlayBooksLogin(self, logged_in=None):
        ui.web_engine.loadedDone()

        if logged_in is None:
            js_code = (
                "var element = Array.from(document.querySelectorAll('span.mdc-button__label')).find("
                "el => el.textContent.trim() === 'Upload files');"
                "if (element) { element.click(); true; } else { false; }"
            )

            ui.web_engine.page().runJavaScript(js_code, lambda result: self.checkPlayBooksLogin(result))
            return

        if not logged_in:
            query_tag = "a[aria-label='Sign in'][href^='https://accounts.google.com/ServiceLogin']"
            js_code = (
                f'var element = document.querySelector("{query_tag}");' + "if (element) {{" + "element.click();" + "}}"
            )

            ui.web_engine.page().runJavaScript(js_code)

            ui.confirmAction(
                "Login Required",
                "Please login to your google account. Click OK when you are done.",
                lambda: (ui.restoreUI(), ui.continue_btn_box.show()),
                info=True,
            )
            return

        QTimer.singleShot(500, lambda: self.handlePlayBooksUpload())

    def handlePlayBooksUpload(self, position=None):
        if position is None:

            js_code = """
            var iframe = document.getElementById(':0.contentEl');
            if (iframe) {
                var rect = iframe.getBoundingClientRect();
                JSON.stringify({x: rect.x + rect.width / 2, y: rect.y + rect.height / 2});
            } else {
                JSON.stringify(null);
            }
            """

            ui.web_engine.page().runJavaScript(js_code, lambda result: self.handlePlayBooksUpload(result))

            return

        if position == "null":
            QTimer.singleShot(100, lambda: self.handlePlayBooksUpload())
            return

        pos_data = json.loads(position)
        x, y = int(pos_data["x"]), int(pos_data["y"])
        view_pos = ui.web_engine.mapToGlobal(QPoint(x, y))

        file_paths = [QUrl.fromLocalFile(book.file_path) for book in self.books]

        mime_data = QMimeData()
        mime_data.setUrls(file_paths)

        drag = QDrag(ui.web_engine)
        drag.setMimeData(mime_data)

        cursor = QCursor()

        QTimer.singleShot(
            2000,
            lambda: (
                cursor.setPos(view_pos.x(), view_pos.y()),
                drag.exec_(Qt.CopyAction),
                self.cleanupPlayBooks(),
            ),
        )

    def cleanupPlayBooks(self, upload_in_progress=True):
        if upload_in_progress:
            js_code = """
            var element = document.getElementById(':0.contentEl');
            if (element) {
                true;
            } else {
                false;
            }
            """

            ui.web_engine.page().runJavaScript(
                js_code,
                lambda result: QTimer.singleShot(500, lambda: self.cleanupPlayBooks(result)),
            )

            return

        if not upload_in_progress:
            ui.confirmAction(
                "Delete Source Files",
                "Would you like to delete the source files for the uploaded books?",
                self.deleteSource,
                self.close,
                warn_text=True,
                warn_true=True,
            )

    def deleteSource(self):
        for book in self.books:
            book.deleteBook(True)

        self.close()
