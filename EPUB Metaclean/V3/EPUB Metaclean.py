from tkinter import *
from tkinter.ttk import *
from PIL import Image, ImageTk
import gc
import os
import shutil
import epubfile
import traceback
import threading
import queue
import requests
import re
import ebookmeta
import sys
from io import BytesIO
from time import sleep
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc


class Window:
    GAP = 0.003
    PADDING = 5
    BORDER = 5
    RELIEF = RIDGE
    FONT = "Helvetica"
    FONT_SIZE = 14
    DEFAULT_IMAGE_URL = "https://images.squarespace-cdn.com/content/v1/5fc7868e04dc9f2855c99940/32f738d4-e4b9-4c61-bfc0-e813699cdd3c/laura-barrett-illustrator-beloved-girls-book-cover.jpg"
    DISABLED_COLOR = "#636363"

    def __init__(self):
        self.root = Tk()
        self.is_running = True
        self.gui_update_queue = queue.Queue()
        self.style = Style()

        self.root.title("EPUB Metaclean V3")
        # self.root.state("zoomed")
        self.root.minsize(1200, 600)
        self.root.config(
            background="black",
            padx=self.PADDING,
            pady=self.PADDING,
            borderwidth=self.BORDER,
            relief=self.RELIEF,
        )

        self.style.theme_create(
            "EMCTheme",
            parent="alt",
            settings={
                "TFrame": {
                    "configure": {
                        "background": "black",
                        "borderwidth": self.BORDER,
                        "relief": self.RELIEF,
                    },
                },
                "NB.TFrame": {
                    "configure": {
                        "borderwidth": 0,
                        "relief": FLAT,
                    },
                },
                "TEntry": {
                    "configure": {
                        "foreground": "green",
                        "fieldbackground": "black",
                        "padding": self.PADDING,
                        "insertcolor": "white",
                    },
                },
                "TLabel": {
                    "configure": {
                        "foreground": "green",
                        "background": "black",
                        "font": (self.FONT, self.FONT_SIZE),
                    }
                },
                "Red.TLabel": {"configure": {"foreground": "red"}},
                "Confirm.TLabel": {
                    "configure": {"font": (self.FONT, self.FONT_SIZE, "bold")}
                },
                "TButton": {
                    "configure": {
                        "foreground": "black",
                        "background": "white",
                        "font": (self.FONT, self.FONT_SIZE),
                        "padding": self.PADDING / 2,
                        "borderwidth": 2,
                        "relief": RAISED,
                        "anchor": "center",
                    },
                    "map": {
                        "background": [
                            ("disabled", self.DISABLED_COLOR),
                            ("active", "green"),
                            ("pressed", "darkgreen"),
                        ],
                        "foreground": [("active", "white")],
                        "relief": [("disabled", FLAT), ("pressed", SUNKEN)],
                    },
                },
                "Red.TButton": {
                    "map": {
                        "background": [
                            ("disabled", "#636363"),
                            ("active", "red"),
                            ("pressed", "darkred"),
                        ],
                    },
                },
                "TScrollbar": {
                    "configure": {"background": "white", "relief": RAISED},
                    "map": {
                        "background": [("active", "green")],
                        "relief": [("pressed", SUNKEN)],
                    },
                },
                "TProgressbar": {
                    "configure": {
                        "background": "green",
                        "troughcolor": "black",
                    }
                },
            },
        )
        self.style.theme_use("EMCTheme")

        self.CreateLayout()
        self._wrap_methods()

        self.right_frame.bind("<Configure>", self.AutoResizeImage)
        self.UpdateImage(self.DEFAULT_IMAGE_URL)

        self.poll_updates_task = self.root.after(100, self._poll_gui_updates)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        self.is_running = False
        queue_lock = threading.Lock()

        with queue_lock:
            self.gui_update_queue = queue.Queue()

        if hasattr(self, "poll_updates_task") and self.poll_updates_task:
            self.root.after_cancel(self.poll_updates_task)
            self.poll_updates_task = None

        for obj in gc.get_objects():
            if isinstance(obj, uc.Chrome):
                try:
                    obj.quit()
                except:
                    pass

        self.root.quit()
        self.root.after(100, self.root.destroy)
        sys.exit()

    def _gui_update(self, func, update_idle):
        def wrapper(*args, **kwargs):
            if self.is_running:
                self.gui_update_queue.put(lambda: func(*args, **kwargs))
                self.gui_update_queue.put(lambda: update_idle())

        return wrapper

    def _poll_gui_updates(self):
        if self.is_running:
            while not self.gui_update_queue.empty():
                update_function = self.gui_update_queue.get()
                update_function()

            self.poll_updates_task = self.root.after(
                100, self._poll_gui_updates
            )

    def _wrap_methods(self):
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and not attr_name.startswith("_"):
                wrapped = self._gui_update(attr, self._update_idle_tasks)
                setattr(self, attr_name, wrapped)

    def _update_idle_tasks(self):
        self.root.update_idletasks()
        self.middle_canvas.configure(
            scrollregion=self.middle_canvas.bbox("all")
        )
        self.middle_canvas.yview_moveto(1.0)

    def CreateLayout(self):
        self.CreateLeftFrame()
        self.CreateRightFrame()
        self.ShowTaskButtons()

    def CreateLeftFrame(self):
        self.left_frame = Frame(self.root, padding=self.PADDING + self.BORDER)
        self.left_frame.place(
            relwidth=(2 - self.GAP) / 3, relheight=1.0, relx=0.0, rely=0.0
        )

        self.top_frame = Frame(self.left_frame, padding=self.PADDING)
        self.top_frame.pack(side="top", anchor="n", fill=X)
        self.progress_bar_label = Label(self.top_frame)
        self.progress_bar = Progressbar(
            self.top_frame, orient=HORIZONTAL, mode="determinate"
        )
        self.progress_bar_percent = Label(self.top_frame)
        self.process_files_button = Button(
            self.top_frame,
            text="Process EPUB Files",
        )
        self.download_book_button = Button(
            self.top_frame, text="Download New Books"
        )
        self.upload_books_button = Button(
            self.top_frame, text="Upload To Play Books"
        )
        self.archive_books_button = Button(
            self.top_frame, text="Move To Arvhive"
        )

        self.middle_frame = Frame(self.left_frame, padding=self.PADDING)
        self.middle_frame.pack(side="top", anchor="n", fill=BOTH, expand=True)
        self.middle_canvas = Canvas(
            self.middle_frame,
            background="black",
            highlightbackground="black",
        )
        self.middle_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        self.middle_scrollbar = Scrollbar(
            self.middle_frame,
            orient=VERTICAL,
            command=self.middle_canvas.yview,
        )
        self.middle_scrollbar.pack(side=RIGHT, fill=Y, padx=(self.PADDING, 0))
        self.middle_canvas.configure(yscrollcommand=self.middle_scrollbar.set)
        self.progress_window = Frame(self.middle_canvas, style="NB.TFrame")
        self.middle_canvas.create_window(
            (0, 0), window=self.progress_window, anchor="nw"
        )

        self.bottom_frame = Frame(
            self.left_frame, padding=self.PADDING, height=45
        )
        self.bottom_frame.pack(
            side="bottom", anchor="s", fill=X, pady=(self.PADDING, 0)
        )
        self.text_input_label = Label(self.bottom_frame)
        self.text_input = Entry(
            self.bottom_frame, font=(self.FONT, self.FONT_SIZE)
        )
        self.text_enter_button = Button(self.bottom_frame)
        self.confirm_button = Button(self.bottom_frame)
        self.reject_button = Button(self.bottom_frame, style="Red.TButton")
        self.manual_button = Button(self.bottom_frame)
        self.prev_button = Button(self.bottom_frame)
        self.select_button = Button(self.bottom_frame)
        self.next_button = Button(self.bottom_frame)
        self.skip_button = Button(self.bottom_frame, style="Red.TButton")

    def InsertSpacerFrame(self, container):
        Label(container, text="   ").pack(fill=X)

    def HideFrame(self, frame):
        for widget in frame.winfo_children():
            widget.pack_forget()

    def ShowProgressBar(self, label=None):
        if label:
            self.progress_bar_label.config(text=label)

        self.progress_bar["value"] = 0
        self.progress_bar_percent.config(text="0.0%")

        self.progress_bar_label.pack(side=LEFT)
        self.progress_bar.pack(
            fill=BOTH, expand=True, side=LEFT, padx=self.PADDING
        )
        self.progress_bar_percent.pack(side=LEFT, padx=(0, self.PADDING))

    def UpdateProgressBar(self, progress=1, override=False):
        self.progress_bar["value"] += progress

        if override:
            self.progress_bar["value"] = progress

        progress_percent = (
            self.progress_bar["value"] / self.progress_bar["maximum"]
        ) * 100
        progress_percent = round(progress_percent, 2)
        self.progress_bar_percent.config(text=f"{progress_percent}%")

    def ShowTaskButtons(self):
        self.process_files_button.pack(fill=BOTH, expand=True, side=LEFT)
        self.download_book_button.pack(fill=BOTH, expand=True, side=LEFT)
        self.upload_books_button.pack(fill=BOTH, expand=True, side=LEFT)
        self.archive_books_button.pack(fill=BOTH, expand=True, side=LEFT)

    def ShowTextInput(self):
        self.text_input_label.pack(side=LEFT, fill=Y)
        self.text_input.pack(side=LEFT, fill=BOTH, expand=True)
        self.text_enter_button.pack(side=LEFT, fill=Y)

    def ShowConfirmInput(self):
        self.confirm_button.pack(fill=X, expand=True, side=LEFT)
        self.reject_button.pack(fill=X, expand=True, side=RIGHT)

    def ShowNavInput(self):
        self.manual_button.pack(side=LEFT, fill=X, expand=True)
        self.prev_button.pack(side=LEFT, fill=X, expand=True)
        self.select_button.pack(side=LEFT, fill=X, expand=True)
        self.next_button.pack(side=LEFT, fill=X, expand=True)
        self.skip_button.pack(side=LEFT, fill=X, expand=True)

    def CreateRightFrame(self):
        self.right_frame = Frame(self.root, padding=self.PADDING)
        self.right_frame.place(
            relwidth=(1 - self.GAP) / 3,
            relheight=1.0,
            relx=(2 + self.GAP) / 3,
            rely=0.0,
        )

        self.image_window = Label(self.right_frame)
        self.image_window.pack(fill=BOTH, expand=True)

    def UpdateImage(self, image_url=None, image_data=None):
        if image_url or image_data:
            if image_url:
                response = requests.get(
                    image_url, stream=True, headers=HEADERS
                )
            self.image_original = Image.open(
                BytesIO(response.content if image_url else image_data)
            )
            self.image_original = self.image_original.resize(
                (1600, 2560), Image.Resampling.LANCZOS
            )
        self.ResizeImage()

    def ResizeImage(self):
        width = self.right_frame.winfo_width()
        height = self.right_frame.winfo_height()

        if self.image_original and width > 1 and height > 1:
            resized_image = self.image_original.copy()
            resized_image.thumbnail((width, height), Image.Resampling.LANCZOS)
            self.image_tk = ImageTk.PhotoImage(resized_image)
            self.image_window.config(image=self.image_tk)
            self.image_window.image = self.image_tk

    def AutoResizeImage(self, event):
        self.ResizeImage()

    def Pack(self, widget, fill=X, *args, **kwargs):
        widget.pack(*args, fill=fill, **kwargs)

    def Config(self, widget, **kwargs):
        widget.config(**kwargs)

    def Destroy(self, widget):
        widget.destroy()


ui = Window()
CURRENT_FOLDER = os.getcwd() + "\\"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/538.39 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
SOURCE_FOLDER = CURRENT_FOLDER + "Source\\"
CHROME_PROFILE = CURRENT_FOLDER + "Chrome Profile\\"
COMPLETED_FOLDER = CURRENT_FOLDER + "Completed\\"
IN_PROGRESS_FOLDER = CURRENT_FOLDER + "In Progress\\"
ERRORED_FOLDER = CURRENT_FOLDER + "Errored\\"
ARCHIVE_FOLDER = CURRENT_FOLDER + "Archive\\"
STRING_TO_REMOVE = "OceanofPDF.com"
GOOD_READS_URL = "https://www.goodreads.com"
GOOD_READS_DEFAULT_IMAGE = (
    "https://dryofg8nmyqjw.cloudfront.net/images/no-cover.png"
)
DOWNLOAD_STAGES = 5
PROCESS_STAGES = 9
UPLOAD_STAGES = 7


# region General Utility Functions
def Setup():
    ui.Config(ui.download_book_button, command=DownloadNewBook)
    ui.Config(ui.process_files_button, command=ProcessFiles)
    ui.Config(ui.upload_books_button, command=UploadBooks)
    ui.Config(ui.archive_books_button, command=MoveToArchive)

    CheckFolders()
    CheckFiles()


def CheckFolders():
    thread = threading.Thread(target=CheckFoldersWorker, daemon=True)
    thread.start()


def CheckFoldersWorker():
    folders = [
        SOURCE_FOLDER,
        COMPLETED_FOLDER,
        IN_PROGRESS_FOLDER,
        ERRORED_FOLDER,
        ARCHIVE_FOLDER,
    ]

    for folder in folders:
        if not os.path.exists(folder):
            os.mkdir(folder)


def CheckFiles():
    thread = threading.Thread(target=CheckFilesWorker, daemon=True)
    thread.start()


def CheckFilesWorker():
    source_files = [
        f for f in os.listdir(SOURCE_FOLDER) if f.endswith(".epub")
    ]
    completed_files = [
        f for f in os.listdir(COMPLETED_FOLDER) if f.endswith(".epub")
    ]

    ui.Config(
        ui.process_files_button,
        state=("normal" if source_files else "disabled"),
    )
    ui.Config(
        ui.archive_books_button,
        state=("normal" if completed_files else "disabled"),
    )
    ui.Config(
        ui.upload_books_button,
        state=("normal" if completed_files else "disabled"),
    )


def CheckFileInFolder(file_name, directory):
    if os.path.exists(directory + file_name):
        subtask_log = DisplayLabel(
            "Error - File Already Exists In Folder!", True
        )

        if InputConfirm("Do You Want To Replace This File?"):
            os.remove(directory + file_name)
        else:
            file_counter = 1
            temp_name = file_name

            while os.path.exists(directory + temp_name):
                temp_name = temp_name.replace(".epub", "")
                end_chars = temp_name.split(" ")[-1]

                if re.search(r"\(\d+\)", end_chars):
                    temp_name = re.sub(r" \(\d+\)", "", temp_name)

                temp_name = f"{temp_name} ({file_counter}).epub"
                file_counter += 1

            file_name = temp_name

        ui.Destroy(subtask_log)

    return file_name


def WaitForInput(input):
    while True:
        CheckRunningState()

        if input.get():
            break
        else:
            sleep(0.1)


def FixQuery(input_string):
    replacements = [f"_{STRING_TO_REMOVE}_", "-", "_", "(", ")", ".epub"]
    temp_string = input_string

    for part in replacements:
        temp_string = temp_string.replace(part, " ")

    query_normal = " ".join(temp_string.split())
    query = "+".join(temp_string.split())

    return [query, query_normal]


def CheckRunningState():
    if not ui.is_running:
        sys.exit()


def GetFolderName(folder):
    return folder.split("\\")[-2]


def GetResponse(url, query_parameters={}):
    while True:
        CheckRunningState()

        try:
            response = requests.get(
                url, query_parameters, headers=HEADERS, timeout=15
            )
            return response
        except requests.exceptions.Timeout:
            sleep(1)
        except Exception as e:
            return requests.Response()


def DisplayLabel(text="", error=False):
    label = Label(
        ui.progress_window,
        text=text,
        style="Red.TLabel" if error else "TLabel",
    )
    ui.Pack(label)

    return label


def UpdateLabel(source_label, text="", error=False):
    ui.Config(
        source_label, text=text, style="Red.TLabel" if error else "TLabel"
    )


def MoveFile(file_name, source, destination, copy=False):
    mode = "Copied" if copy else "Moved"
    mode_during = "Copying" if copy else "Moving"
    subtask = DisplayLabel(
        f" - {mode_during} {file_name} To {GetFolderName(destination)}..."
    )

    new_file_name = CheckFileInFolder(file_name, destination)
    file_paths = (source + file_name, destination + new_file_name)

    if copy:
        shutil.copy(file_paths[0], file_paths[1])
    else:
        shutil.move(file_paths[0], file_paths[1])

    UpdateLabel(
        subtask, f" - {new_file_name} {mode} To {GetFolderName(destination)}!"
    )

    return new_file_name, destination


# endregion


# region Input Handlers
def InputConfirm(
    text="ARE YOU SURE?",
    accept_text="Yes",
    reject_text="No",
    accept_only=False,
    confirm=False,
):
    text = f"\n * {text} *"
    user_action = StringVar()

    ui.Config(ui.confirm_button, text=accept_text)
    ui.Config(
        ui.reject_button,
        text=reject_text,
        state="disabled" if accept_only else None,
    )

    ui.HideFrame(ui.bottom_frame)
    ui.ShowConfirmInput()

    confirm_label = DisplayLabel(text)

    ui.Config(ui.confirm_button, command=lambda: user_action.set(True))
    ui.Config(ui.reject_button, command=lambda: user_action.set(False))
    WaitForInput(user_action)

    ui.Destroy(confirm_label)
    ui.HideFrame(ui.bottom_frame)

    ui.Config(ui.reject_button, state="normal") if accept_only else None

    response = bool(int(user_action.get()))

    if confirm and not response:
        response = InputConfirm()

    return response


def InputText(text="", label_text="Search Term:", button_text="Enter"):
    text = f"\n * {text} *"
    user_input = StringVar()

    ui.Config(ui.text_input_label, text=label_text)
    ui.Config(ui.text_enter_button, text=button_text)

    ui.HideFrame(ui.bottom_frame)
    ui.ShowTextInput()

    text_label = DisplayLabel(text)

    ui.Config(
        ui.text_enter_button,
        command=lambda: user_input.set(
            ui.text_input.get() if ui.text_input.get() else "skip"
        ),
    )

    WaitForInput(user_input)

    ui.text_input.delete(0, END)

    ui.Destroy(text_label)
    ui.HideFrame(ui.bottom_frame)

    return user_input.get()


def InputNav(
    total,
    index=0,
    manual_text="Manual",
    prev_text="Prev",
    select_text="Select",
    next_text="Next",
    skip_text="Skip",
    disable_select=False,
):
    state = ["normal", "disabled"]
    user_action = StringVar()

    ui.Config(ui.manual_button, text=manual_text)
    ui.Config(
        ui.next_button,
        text=next_text,
        state=state[0] if index < total - 1 else state[1],
    )
    ui.Config(
        ui.select_button,
        text=select_text,
        state=state[0] if total > 0 else state[1],
    )
    ui.Config(ui.select_button, state=state[1]) if disable_select else None
    ui.Config(
        ui.prev_button,
        text=prev_text,
        state=state[0] if index > 0 else state[1],
    )
    ui.Config(ui.skip_button, text=skip_text if skip_text else "Skip")

    ui.HideFrame(ui.bottom_frame)
    ui.ShowNavInput()

    ui.Config(ui.manual_button, command=lambda: user_action.set("manual"))
    ui.Config(ui.skip_button, command=lambda: user_action.set("skip"))
    ui.Config(ui.next_button, command=lambda: user_action.set("next"))
    ui.Config(ui.select_button, command=lambda: user_action.set("select"))
    ui.Config(ui.prev_button, command=lambda: user_action.set("prev"))

    WaitForInput(user_action)

    ui.HideFrame(ui.bottom_frame)

    return user_action.get()


# endregion


# region Selenium Functions
def CreateChromeDriver():
    subtask = DisplayLabel(" - Creating Automated Chrome Window...")
    options = uc.ChromeOptions()

    preferences_file = CHROME_PROFILE + "\\Default\\Preferences"
    if os.path.exists(preferences_file):
        os.remove(preferences_file)

    options.add_argument(f"--user-data-dir={CHROME_PROFILE}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--disable-notifications")
    options.add_experimental_option(
        "prefs", {"download.default_directory": SOURCE_FOLDER}
    )
    web_driver = uc.Chrome(options=options)
    web_driver.minimize_window()

    UpdateLabel(subtask, " - Chrome Window Created!")

    return web_driver


def SetDriverSize(web_driver):
    web_driver.execute_script("window.focus();")
    web_driver.set_window_size(width=100, height=400)


def FindElement(web_driver, element, wait_time=15, click=False):
    time_waited = 0

    while time_waited <= wait_time:
        CheckRunningState()

        try:
            found_element = WebDriverWait(web_driver, 1).until(
                EC.presence_of_element_located(element)
            )

            if click:
                found_element.click()
                return True
            else:
                return found_element
        except:
            time_waited += 1

    return False


def FindElements(web_driver, element, wait_time=15):
    time_waited = 0

    while time_waited <= wait_time:
        CheckRunningState()

        try:
            found_elements = WebDriverWait(web_driver, 1).until(
                EC.presence_of_all_elements_located(element)
            )
            return found_elements
        except:
            time_waited += 1

    return False


def ClearDriverTabs(web_driver):
    subtask = DisplayLabel(" - Clearing Extra Tabs...")
    SetDriverSize(web_driver)

    while len(web_driver.window_handles) > 1:
        web_driver.close()
        web_driver.switch_to.window(web_driver.window_handles[0])

    web_driver.minimize_window()
    UpdateLabel(subtask, " - Extra Tabs Cleared!")


# endregion


# region Process Files Functions
def CleanBook(file_path):
    subtask = DisplayLabel(" - Cleaning Book Content...")
    book = epubfile.Epub(file_path)

    for page in book.get_texts():
        soup = book.read_file(page)
        soup = soup.replace(STRING_TO_REMOVE, "")
        book.write_file(page, soup)

    UpdateLabel(subtask, " - Book Content Cleaned!")


def SearchGoodReads(input):
    query = FixQuery(input)
    results = []
    current_index = 0
    book_template = {
        "book_title": None,
        "book_author": None,
        "book_series": None,
        "book_series_index": None,
        "book_cover": None,
    }
    subtask = DisplayLabel(f" - Searching {query[1]} On GoodReads...")

    def manual_search():
        UpdateLabel(subtask, f" - Manual GoodReads Search:")
        new_search = InputText(
            text="Please Enter Your Search Term\n - (Leave Blank To Skip)"
        )
        if new_search == "skip":
            return False
        return FixQuery(new_search)

    def get_book_details(book_soup):
        book_title = book_soup.select(".bookTitle")[0].text.strip()
        book_author = book_soup.select(".authorName")[0].text.strip()
        book_series = None
        book_series_index = None

        if re.search(r", #\d+", book_title):
            book_series = book_title.split("(")[1].split(")")[0]
            book_series = re.sub(r", #\d+", "", book_series)
            book_series_index = float(
                re.search(r", #(\d+)", book_title).group(1)
            )

        book_url = GOOD_READS_URL + book_soup.select(".bookTitle")[0]["href"]
        response = GetResponse(book_url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            book_cover = soup.select(".BookCover__image")[0].select("img")[0][
                "src"
            ]

        return {
            "book_title": book_title,
            "book_author": book_author,
            "book_series": book_series,
            "book_series_index": book_series_index,
            "book_cover": book_cover,
        }

    def display_result(index):
        UpdateLabel(
            subtask, f" - Result {index + 1} Of {len(results)} For {query[1]}:"
        )
        book_data = get_book_details(results[index])
        subtask_log_text = f"\n * Book Title: {book_data['book_title']}\n\n"
        subtask_log_text += f" * Book Author: {book_data['book_author']}\n\n"

        if book_data["book_series"]:
            subtask_log_text += (
                f" * Book Series: {book_data['book_series']}\n\n"
            )
            subtask_log_text += (
                f" * Book Series Index: {book_data['book_series_index']}"
            )

        UpdateLabel(subtask_log, subtask_log_text)
        ui.UpdateImage(book_data["book_cover"])

        return book_data

    while True:
        CheckRunningState()

        book_data = {}
        url = f"{GOOD_READS_URL}/search?q={query[0]}"
        response = GetResponse(url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            results = soup.select("tr")
            current_index = 0

            if not results:
                UpdateLabel(subtask, f" - No Results For {query[1]}!")

            while True:
                CheckRunningState()

                subtask_log = DisplayLabel()

                if results:
                    loading_label = DisplayLabel("Loading...")
                    book_data = display_result(current_index)
                    ui.Destroy(loading_label)

                user_action = InputNav(len(results), current_index)
                ui.Destroy(subtask_log)

                match (user_action):
                    case "manual":
                        query = manual_search()
                        if not query:
                            return book_template
                        break
                    case "skip":
                        if InputConfirm(
                            "Are You Sure You Want To Skip The Meta Search?"
                        ):
                            UpdateLabel(
                                subtask,
                                " - GoodReads Book Search Skipped!",
                                True,
                            )
                            ui.HideFrame(ui.bottom_frame)
                            return book_template
                    case "next":
                        current_index += 1
                    case "prev":
                        current_index += -1
                    case "select":
                        UpdateLabel(
                            subtask, " - GoodReads Book Search Completed!"
                        )
                        ui.HideFrame(ui.bottom_frame)
                        return book_data


def GetCoverID(book):
    cover_id = None
    false_positives = ["images/cover.png"]

    try:
        cover_id = book.get_cover_image()
    except:
        pass

    if not cover_id or cover_id in false_positives:
        possible_tags = [
            "coverimagestandard",
            "cover.png",
            "cover-image",
            "cover",
        ]

        for tag in possible_tags:
            try:
                book.get_manifest_item(tag)
                cover_id = tag
            except:
                continue

            if cover_id:
                break

    if not cover_id:
        print("Possible Tags:")
        for item in book.get_manifest_items():
            print(item)

        DisplayLabel(
            "Error - Cover Tag Could Not Be Found!\n - Please Check Terminal Log For Possible Tags\n - Please Submit These And Epub File On Github For Fixes",
            True,
        )
        return None

    return cover_id


def GetCover(url, file):
    skip_confirm = False
    subtask = DisplayLabel(f" - Confirming Cover Image...")
    subtask_log = DisplayLabel()

    book = epubfile.Epub(file)
    cover_id = GetCoverID(book)

    if url == GOOD_READS_DEFAULT_IMAGE and cover_id:
        UpdateLabel(
            subtask_log, " - Missing Book Cover!, Pulling From EPUB..."
        )
        ui.UpdateImage(image_data=book.read_file(cover_id))

    while cover_id:
        url = None

        if skip_confirm or not InputConfirm(
            "Do You Want To Use This Cover?", confirm=True
        ):
            skip_confirm = False
            formats = (".jpg", ".jpeg", ".png")

            url = InputText(
                text="Please Enter An Image URL\n - (Leave Blank To Use Default)",
                label_text="URL:",
            )

            if url == "skip":
                url = GOOD_READS_DEFAULT_IMAGE

            if not url.lower().endswith(formats):
                skip_confirm = True
                UpdateLabel(
                    subtask_log,
                    "Not Accepted Format, Must Be JPG or PNG!",
                    True,
                )
                continue

            if not GetResponse(url).status_code == 200:
                skip_confirm = True
                UpdateLabel(
                    subtask_log,
                    "Error - Image Not Found, Please Try Again!",
                    True,
                )
                continue

            ui.UpdateImage(url)
        else:
            ui.Destroy(subtask_log)
            break

    if not cover_id:
        UpdateLabel(
            subtask,
            " - Unable To Retrieve Cover ID In Manifest!",
        )
        return False

    UpdateLabel(subtask, " - Cover Image Confirmed!")

    img = ui.image_original.convert("RGB")
    img_data = BytesIO()
    img.save(img_data, format="jpeg")

    return img_data.getvalue()


def UpdateMetadata(book_data, file):
    subtask = DisplayLabel(" - Updating Book Metadata...")
    subtask_log = DisplayLabel(" * Getting Data From Book...")
    meta = ebookmeta.get_metadata(file)

    def update_book_data(text, new_data, old_data):
        UpdateLabel(subtask_log, f" * {text} Updated!")
        return book_data[new_data] if book_data[new_data] else old_data

    meta.title = update_book_data("Title", "book_title", meta.title)
    meta.set_author_list_from_string(
        update_book_data(
            "Authors", "book_author", meta.author_list_to_string()
        )
    )
    meta.series = update_book_data("Series", "book_series", meta.series)
    meta.series_index = update_book_data(
        "Series Index", "book_series_index", meta.series_index
    )
    ebookmeta.set_metadata(file, meta)

    if book_data["book_cover"]:
        book = epubfile.Epub(file)
        cover_id = GetCoverID(book)
        book.write_file(cover_id, book_data["book_cover"])
        book.save(file)
        UpdateLabel(subtask_log, " * Cover Updated!")
    ui.Destroy(subtask_log)

    UpdateLabel(subtask, " - Book Metadata Updated!")


def RenameFile(file_name, directory):
    subtask = DisplayLabel(" - Renaming EPUB File...")
    meta = ebookmeta.get_metadata(directory + file_name)

    new_name = f"{meta.title} - "
    new_name += meta.author_list_to_string().replace(", ", " - ")
    new_name = new_name.replace(":", "") + ".epub"
    if not new_name == file_name:
        new_name = CheckFileInFolder(new_name, directory)

        os.rename(directory + file_name, directory + new_name)

    UpdateLabel(subtask, f" - EPUB File Renamed: {new_name}")
    return new_name


def DeleteSourceFiles(file_name):
    subtask = DisplayLabel(" - Deleting Source File...")

    if InputConfirm("Would You Like To Delete The Source File?"):
        if os.path.exists(SOURCE_FOLDER + file_name):
            os.remove(SOURCE_FOLDER + file_name)
            UpdateLabel(subtask, " - Source File Deleted!")
        else:
            DisplayLabel(f"{file_name} Not Found In {SOURCE_FOLDER}!")
    else:
        UpdateLabel(subtask, " - Source File Not Deleted!")


def ProcessFiles():
    thread = threading.Thread(target=ProcessFilesWorker, daemon=True)
    thread.start()


def ProcessFilesWorker():
    files = [f for f in os.listdir(SOURCE_FOLDER) if f.endswith(".epub")]
    ui.Config(ui.progress_bar, maximum=PROCESS_STAGES * len(files))
    task_label = DisplayLabel(f"Processing {len(files)} Files...")

    ui.HideFrame(ui.top_frame)
    ui.ShowProgressBar("Processing Files:")

    for index, file_name in enumerate(files):
        task = DisplayLabel(f"Would You Like To Process This File?")
        source_file_name = file_name

        if not InputConfirm(file_name):
            UpdateLabel(task, f"Skipping File: {file_name}!", True)
            ui.InsertSpacerFrame(ui.progress_window)
            ui.UpdateProgressBar(PROCESS_STAGES * (index + 1), True)
            continue

        UpdateLabel(task, f"Processing File: {file_name}...")

        try:
            current_directory = SOURCE_FOLDER
            file_name, current_directory = MoveFile(
                file_name, current_directory, IN_PROGRESS_FOLDER, True
            )
            ui.UpdateProgressBar()

            CleanBook(current_directory + file_name)
            ui.UpdateProgressBar()

            book_data = SearchGoodReads(file_name)
            ui.UpdateProgressBar()

            book_data["book_cover"] = GetCover(
                book_data["book_cover"], current_directory + file_name
            )
            ui.UpdateProgressBar()

            UpdateMetadata(book_data, current_directory + file_name)
            ui.UpdateProgressBar()

            file_name = RenameFile(file_name, current_directory)
            ui.UpdateProgressBar()

            file_name, current_directory = MoveFile(
                file_name, current_directory, COMPLETED_FOLDER
            )
            ui.UpdateProgressBar()

            DeleteSourceFiles(source_file_name)
            ui.UpdateProgressBar()

            UpdateLabel(task, f"Processing File: {file_name}, Done!")
            ui.UpdateProgressBar()

            ui.InsertSpacerFrame(ui.progress_window)
            ui.UpdateImage(ui.DEFAULT_IMAGE_URL)
        except Exception as e:
            UpdateLabel(task, f"Processing File: {file_name} - FAILED!", True)
            ui.UpdateProgressBar(PROCESS_STAGES * (index + 1), True)
            tb = traceback.format_exc()
            print(tb)
            last_line = tb.strip().split("\n")[-1]

            ui.InsertSpacerFrame(ui.progress_window)
            DisplayLabel(f"Error Details: {last_line}", True)
            MoveFile(file_name, current_directory, ERRORED_FOLDER)
            ui.InsertSpacerFrame(ui.progress_window)

    UpdateLabel(task_label, f"Processing {len(files)} Files, Done!")
    ui.HideFrame(ui.top_frame)
    ui.ShowTaskButtons()
    CheckFiles()


# endregion


# region Google Upload Functions
def CheckGoogleSignIn(web_driver):
    subtask = DisplayLabel(" - Checking If You Are Logged In...")

    while True:
        web_driver.get("https://play.google.com/books/uploads")
        element = (By.XPATH, "//span[text()='Sign in']")

        if not FindElement(web_driver, element, wait_time=2, click=True):
            UpdateLabel(subtask, " - Logged In!")
            return True

        subtask_label = DisplayLabel("Not Logged In, Please Login Now.", True)
        web_driver.maximize_window()
        response = InputConfirm(
            text="Please Click Done When You Have Logged In.",
            accept_text="Done",
            reject_text="Cancel",
        )
        SetDriverSize()
        web_driver.minimize_window()
        ui.Destroy(subtask_label)

        if not response:
            UpdateLabel(subtask, " - Login Cancelled!", True)
            return False


def OpenGoogleUploadDialog(web_driver):
    element = (By.XPATH, "//span[text()='\n      Upload files']")
    subtask = DisplayLabel(" - Accessing Upload Dialog...")

    SetDriverSize(web_driver)

    if not FindElement(web_driver, element, click=True):
        UpdateLabel(subtask, " - Failed To Access Upload Dialog!", True)
        return False

    web_driver.minimize_window()

    UpdateLabel(subtask, " - Upload Dialog Opened!")
    return True


def CollectFilesForUpload(files):
    file_paths = []
    subtask = DisplayLabel(" - Collecting EPUB Files...")

    for file_name in files:
        ui.UpdateProgressBar()
        subtask_log = DisplayLabel(f"\n * {file_name}")
        if InputConfirm("Would You Like To Upload This File?"):
            file_paths.append(os.path.join(COMPLETED_FOLDER, file_name))
            UpdateLabel(subtask_log, f" - {file_name} Added To Queue")
            continue

        UpdateLabel(subtask_log, f" - {file_name} Skipped!")

    if len(file_paths) == 0:
        UpdateLabel(subtask, " - All Files Skipped, Nothing To Upload!", True)
        return False

    UpdateLabel(subtask, " - EPUB Files Collected!")
    return file_paths


def UploadEpubFiles(web_driver, files):
    subtask = DisplayLabel(" - Uploading Files To Play Books...")
    element = (By.ID, ":0.contentEl")

    SetDriverSize(web_driver)
    iframe = FindElement(web_driver, element)

    if not iframe:
        UpdateLabel(
            " - Unable To Locate IFrame Container! - Blame Google!", True
        )
        return False

    element = (By.TAG_NAME, "iframe")
    iframe = FindElement(iframe, element)

    if not iframe:
        UpdateLabel(" - Unable To Locate IFrame! - Blame Google!", True)
        return False

    web_driver.switch_to.frame(iframe)

    element = (By.XPATH, "//input[@type='file']")
    file_input = FindElement(web_driver, element)

    if not file_input:
        UpdateLabel(" - Unable To Locate File Input! - Blame Google!", True)
        return False

    file_paths = "\n".join(files)
    file_input.send_keys(file_paths)

    web_driver.switch_to.default_content()

    UpdateLabel(subtask, " - Files Added To Play Books Upload Queue!")
    return True


def WaitForUpload(web_driver):
    subtask = DisplayLabel(" - Waiting For Upload")
    element = (By.ID, ":0.contentEl")

    while True:
        tracker = FindElement(web_driver, element)

        if not tracker:
            break

    web_driver.minimize_window()
    UpdateLabel(subtask, " - Books Uploaded!")


def UploadBooks():
    thread = threading.Thread(target=UploadBooksWorker, daemon=True)
    thread.start()


def UploadBooksWorker():
    ui.HideFrame(ui.top_frame)
    ui.ShowProgressBar("Uploading Files:")

    files = [f for f in os.listdir(COMPLETED_FOLDER) if f.endswith(".epub")]
    task_label = DisplayLabel(f"Uploading {len(files)} Files...")
    ui.Config(ui.progress_bar, maximum=UPLOAD_STAGES + len(files))

    def end_function():
        ui.InsertSpacerFrame(ui.progress_window)
        web_driver.quit()
        ui.HideFrame(ui.top_frame)
        ui.ShowTaskButtons()
        CheckFiles()

    def upload_cancelled():
        UpdateLabel(task_label, "File Upload Cancelled!", True)
        end_function()

    web_driver = CreateChromeDriver()
    ui.UpdateProgressBar()

    if not CheckGoogleSignIn(web_driver):
        upload_cancelled()
        return
    ui.UpdateProgressBar()

    if not OpenGoogleUploadDialog(web_driver):
        upload_cancelled()
        return
    ui.UpdateProgressBar()

    epubs_for_upload = CollectFilesForUpload(files)
    if not epubs_for_upload:
        upload_cancelled()
        return
    ui.UpdateProgressBar()

    if not UploadEpubFiles(web_driver, epubs_for_upload):
        upload_cancelled()
        return
    ui.UpdateProgressBar()

    WaitForUpload(web_driver)
    ui.UpdateProgressBar()

    UpdateLabel(task_label, f"Uploading {len(files)} Files, Done!")
    ui.UpdateProgressBar()
    end_function()


# endregion


# region Archive Files Functions
def MoveToArchive():
    thread = threading.Thread(target=MoveToArchiveWorker, daemon=True)
    thread.start()


def MoveToArchiveWorker():
    ui.HideFrame(ui.top_frame)
    ui.ShowProgressBar("Archiving Files:")

    files = [f for f in os.listdir(COMPLETED_FOLDER) if f.endswith(".epub")]
    task_label = DisplayLabel(f"Archiving {len(files)} Files...")
    ui.Config(ui.progress_bar, maximum=len(files) + 1)

    for file_name in files:
        subtask_log = DisplayLabel(f"\n * {file_name}")
        ui.UpdateProgressBar()

        if InputConfirm("Would You Like To Archive This File?"):
            file_name = CheckFileInFolder(file_name, ARCHIVE_FOLDER)
            MoveFile(file_name, COMPLETED_FOLDER, ARCHIVE_FOLDER)
            ui.Destroy(subtask_log)
            continue

        UpdateLabel(subtask_log, f" - {file_name} Skipped!")
        ui.Destroy(subtask_log)

    UpdateLabel(task_label, f"{len(files)} Files Archived!")
    ui.UpdateProgressBar()
    ui.InsertSpacerFrame(ui.progress_window)


# endregion


# region Download Files Functions
def DownloadEpubFile(web_driver, url, title):
    subtask = DisplayLabel(f" - Downloading {title}...")
    element = (
        By.XPATH,
        "//input[@src='https://media.oceanofpdf.com/epub-button.jpg']",
    )

    old_files_count = len(
        [f for f in os.listdir(SOURCE_FOLDER) if f.endswith(".epub")]
    )

    SetDriverSize(web_driver)
    web_driver.get(url)

    if not FindElement(web_driver, element, click=True):
        web_driver.minimize_window()
        UpdateLabel(
            subtask,
            " - Failed To Find Download Button! - Blame OceanOfPDF!",
            True,
        )
        return
    web_driver.minimize_window()

    waited_time = 0
    while True:
        CheckRunningState()

        new_files_count = len(
            [f for f in os.listdir(SOURCE_FOLDER) if f.endswith(".epub")]
        )

        if new_files_count > old_files_count:
            break

        sleep(1)
        waited_time += 1

        if waited_time == 30:
            if not InputConfirm("Has The Download Failed?"):
                UpdateLabel(subtask, " - Download Has Failed!", True)
                return

    UpdateLabel(subtask, f" - {title} Downloaded!")


def DownloadNewBook():
    thread = threading.Thread(target=DownloadNewBookWorker, daemon=True)
    thread.start()


def DownloadNewBookWorker():
    task_label = DisplayLabel("Downloading New Books...")
    web_driver = CreateChromeDriver()

    def end_function():
        ui.InsertSpacerFrame(ui.progress_window)
        web_driver.quit()
        ui.HideFrame(ui.top_frame)
        ui.ShowTaskButtons()
        CheckFiles()

    def download_cancelled():
        UpdateLabel(task_label, "File Downloads Cancelled!", True)
        end_function()

    def downloads_finished():
        UpdateLabel(task_label, "File Downloads Finished!")
        end_function()

    def get_book_details(book_soup):
        book_title = book_soup.select(".entry-title-link")[0].text.strip()
        book_author = (
            str(book_soup.select(".postmetainfo")[0])
            .split("</strong>")[1]
            .split("<br/>")[0]
        )
        book_release_date = book_soup.select(".entry-time")[0].text.strip()
        book_cover_url = re.sub(
            r"-\d+x\d+", "", book_soup.select(".post-image")[0]["src"]
        )
        book_url = book_soup.select(".entry-title-link")[0]["href"]
        book_has_epub = (
            True if "epub" in re.split(r"[/-]", book_url) else False
        )

        return {
            "book_title": book_title,
            "book_author": book_author,
            "book_release_data": book_release_date,
            "book_cover_url": book_cover_url,
            "book_url": book_url,
            "book_has_epub": book_has_epub,
        }

    def display_result(results_count, index):
        result_data = results[index].get_attribute("outerHTML")
        soup = BeautifulSoup(result_data, "html.parser")
        book_data = get_book_details(soup)

        task_log_text = f" - Result {index} Of {results_count}:\n\n"
        task_log_text += f" * Book Title: {book_data['book_title']}\n\n"
        task_log_text += f" * Book Author: {book_data['book_author']}\n\n"
        task_log_text += f" * Book Published: {book_data['book_release_data']}"

        previous_image = ui.image_original
        ui.UpdateImage(book_data["book_cover_url"])

        while True:
            CheckRunningState()

            if not ui.image_original == previous_image:
                break

            sleep(0.5)

        UpdateLabel(task_log, task_log_text)

        return (
            book_data["book_url"],
            book_data["book_has_epub"],
            book_data["book_title"],
        )

    while True:
        CheckRunningState()

        element = (By.TAG_NAME, "article")
        current_index = 0

        ui.UpdateImage(ui.DEFAULT_IMAGE_URL)
        ui.HideFrame(ui.top_frame)
        ui.ShowProgressBar("Downloading New Book:")
        ui.Config(ui.progress_bar, maximum=DOWNLOAD_STAGES)

        query = FixQuery(
            InputText(
                "What Book Would You Like To Search For?\n - (Leave Blank To Cancel)",
                label_text="Search:",
            )
        )

        if query[1] == "skip":
            if not InputConfirm():
                continue
            download_cancelled()
            return

        task = DisplayLabel(f" - Searching For {query[1]}...")
        ui.UpdateProgressBar()

        web_driver.get(f"https://oceanofpdf.com/?s={query[0]}")
        ui.UpdateProgressBar()

        SetDriverSize(web_driver)
        results = FindElements(web_driver, element, 5)
        web_driver.minimize_window()
        if not results:
            UpdateLabel(task, f" - No Results For {query[1]}!", True)
            continue
        ui.UpdateProgressBar()

        while True:
            CheckRunningState()

            UpdateLabel(task, f" - {len(results)} Results For {query[1]}")

            loading_label = DisplayLabel("Loading...")
            task_log = DisplayLabel()
            result_url, result_has_epub, result_title = display_result(
                len(results), current_index
            )
            ui.Destroy(loading_label)

            user_action = InputNav(
                len(results),
                current_index,
                manual_text="New Search",
                skip_text="Cancel",
                select_text="Select" if result_has_epub else "NO EPUB FOUND",
                disable_select=not result_has_epub,
            )
            ui.Destroy(task_log)

            match (user_action):
                case "manual":
                    ui.InsertSpacerFrame(ui.progress_window)
                    break
                case "skip":
                    if not InputConfirm():
                        continue
                    download_cancelled()
                    return
                case "next":
                    current_index += 1
                case "prev":
                    current_index += -1
                case "select":
                    UpdateLabel(task, f" - Found Result For {query[1]}!")
                    DownloadEpubFile(web_driver, result_url, result_title)
                    ui.UpdateProgressBar()

                    ClearDriverTabs(web_driver)
                    ui.InsertSpacerFrame(ui.progress_window)
                    ui.UpdateProgressBar()

                    if not InputConfirm(
                        "Do You Want To Search For Another Book?"
                    ):
                        downloads_finished()
                        return
                    break


# endregion


def Main():
    Setup()
    ui.root.mainloop()


Main()
