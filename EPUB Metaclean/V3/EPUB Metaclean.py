# region Imports
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

# endregion


# region Classes
class Window:
    GAP = 0.003
    PADDING = 5
    BORDER = 5
    RELIEF = RIDGE
    FONT = "Helvetica"
    FONT_SIZE = 14
    DEFAULT_IMAGE_URL = "https://images.squarespace-cdn.com/content/v1/5fc7868e04dc9f2855c99940/32f738d4-e4b9-4c61-bfc0-e813699cdd3c/laura-barrett-illustrator-beloved-girls-book-cover.jpg"
    DISABLED_COLOR = "#636363"

    class TopFrame:
        def __init__(self, parent):
            self.parent = parent

            self.frame = Frame(parent.left_frame, padding=parent.PADDING)
            self.frame.pack(side="top", anchor="n", fill=X)

            self.progress_bar_label = Label(self.frame)
            self.progress_bar = Progressbar(
                self.frame, orient=HORIZONTAL, mode="determinate"
            )
            self.progress_bar_percent = Label(self.frame)
            self.download_btn = Button(self.frame, text="Download New Books")
            self.process_btn = Button(self.frame, text="Process EPUB Files")
            self.upload_btn = Button(self.frame, text="Upload To Play Books")

        def show_progress_bar(self, label=None):
            if label:
                self.progress_bar_label.config(text=label)

            self.progress_bar["value"] = 0
            self.progress_bar_percent.config(text="0.0%")

            self.progress_bar_label.pack(side=LEFT)
            self.progress_bar.pack(
                fill=BOTH, expand=True, side=LEFT, padx=self.parent.PADDING
            )
            self.progress_bar_percent.pack(
                side=LEFT, padx=(0, self.parent.PADDING)
            )

        def update_progress_bar(self, progress=1, override=False):
            self.progress_bar["value"] += progress

            if override:
                self.progress_bar["value"] = progress

            progress_percent = (
                self.progress_bar["value"] / self.progress_bar["maximum"]
            ) * 100
            progress_percent = round(progress_percent, 2)
            self.progress_bar_percent.config(text=f"{progress_percent}%")

        def show_task_btns(self):
            self.download_btn.pack(fill=BOTH, expand=True, side=LEFT)
            self.process_btn.pack(fill=BOTH, expand=True, side=LEFT)
            self.upload_btn.pack(fill=BOTH, expand=True, side=LEFT)

        def hide(self):
            for widget in self.frame.winfo_children():
                widget.pack_forget()

    class MiddleFrame:
        def __init__(self, parent):
            self.parent = parent

            self.frame = Frame(parent.left_frame, padding=parent.PADDING)
            self.frame.pack(side="top", anchor="n", fill=BOTH, expand=True)

            self.canvas = Canvas(
                self.frame, background="black", highlightbackground="black"
            )
            self.canvas.pack(side=LEFT, fill=BOTH, expand=True)

            self.scrollbar = Scrollbar(
                self.frame, orient=VERTICAL, command=self.canvas.yview
            )
            self.scrollbar.pack(side=RIGHT, fill=Y, padx=(parent.PADDING, 0))
            self.canvas.configure(yscrollcommand=self.scrollbar.set)

            self.content_window = Frame(self.canvas, style="NB.TFrame")
            self.canvas.create_window(
                (0, 0), window=self.content_window, anchor="nw"
            )

        def update_idle_tasks(self):
            self.parent.root.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            self.canvas.yview_moveto(1.0)

    class BottomFrame:
        def __init__(self, parent):
            self.parent = parent

            self.frame = Frame(
                parent.left_frame, padding=parent.PADDING, height=45
            )
            self.frame.pack(
                side="bottom", anchor="s", fill=X, pady=(parent.PADDING, 0)
            )

            self.text_input_label = Label(self.frame)
            self.text_input = Entry(
                self.frame, font=(parent.FONT, parent.FONT_SIZE)
            )
            self.text_input_btn = Button(self.frame)

            self.true_btn = Button(self.frame)
            self.false_btn = Button(self.frame, style="Red.TButton")

            self.manual_btn = Button(self.frame)
            self.prev_btn = Button(self.frame)
            self.select_btn = Button(self.frame)
            self.next_btn = Button(self.frame)
            self.skip_btn = Button(self.frame, style="Red.TButton")

        def show_text_input(self):
            self.text_input_label.pack(side=LEFT, fill=Y)
            self.text_input.pack(side=LEFT, fill=BOTH, expand=True)
            self.text_input_btn.pack(side=LEFT, fill=Y)

        def show_confirm_input(self):
            self.true_btn.pack(fill=X, expand=True, side=LEFT)
            self.false_btn.pack(fill=X, expand=True, side=RIGHT)

        def show_nav_input(self):
            self.manual_btn.pack(side=LEFT, fill=X, expand=True)
            self.prev_btn.pack(side=LEFT, fill=X, expand=True)
            self.select_btn.pack(side=LEFT, fill=X, expand=True)
            self.next_btn.pack(side=LEFT, fill=X, expand=True)
            self.skip_btn.pack(side=LEFT, fill=X, expand=True)

        def hide(self):
            for widget in self.frame.winfo_children():
                widget.pack_forget()

    def __init__(self):
        self.root = Tk()
        self.is_running = True
        self.gui_update_queue = queue.Queue()
        self.style = Style()

        self.root.title("EPUB Metaclean V3")
        self.root.state("zoomed")
        self.root.minsize(1300, 700)
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

        self.create_layout()
        self._wrap_methods()

        self.right_frame.bind("<Configure>", self.auto_resize_image)
        self.update_image(self.DEFAULT_IMAGE_URL)

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
        self.middle_frame.update_idle_tasks()

    def create_layout(self):
        self.left_frame = Frame(self.root, padding=self.PADDING + self.BORDER)
        self.left_frame.place(
            relwidth=(2 - self.GAP) / 3, relheight=1.0, relx=0.0, rely=0.0
        )

        self.top_frame = self.TopFrame(self)
        self.middle_frame = self.MiddleFrame(self)
        self.bottom_frame = self.BottomFrame(self)

        self.right_frame = Frame(self.root, padding=self.PADDING)
        self.right_frame.place(
            relwidth=(1 - self.GAP) / 3,
            relheight=1.0,
            relx=(2 + self.GAP) / 3,
            rely=0.0,
        )

        self.image_window = Label(self.right_frame)
        self.image_window.pack(fill=BOTH, expand=True)

        self.top_frame.show_task_btns()

    def update_image(self, image_url=None, image_data=None):
        if image_url or image_data:
            if image_url:
                response = requests.get(
                    image_url, stream=True, headers=C.HEADERS
                )
            self.image_original = Image.open(
                BytesIO(response.content if image_url else image_data)
            )
            self.image_original = self.image_original.resize(
                (1600, 2560), Image.Resampling.LANCZOS
            )
        self.resize_image()

    def resize_image(self):
        width = self.right_frame.winfo_width()
        height = self.right_frame.winfo_height()

        if self.image_original and width > 1 and height > 1:
            resized_image = self.image_original.copy()
            resized_image.thumbnail((width, height), Image.Resampling.LANCZOS)
            self.image_tk = ImageTk.PhotoImage(resized_image)
            self.image_window.config(image=self.image_tk)
            self.image_window.image = self.image_tk

    def auto_resize_image(self, event):
        self.resize_image()

    def pack(self, widget, *args, **kwargs):
        if "fill" not in kwargs:
            kwargs["fill"] = X

        widget.pack(*args, **kwargs)

    def config(self, widget, **kwargs):
        widget.config(**kwargs)

    def destroy(self, widget):
        widget.destroy()


class Book:
    def __init__(self, **kwargs):
        self.title = None
        self.author = None
        self.series = None
        self.series_index = None
        self.cover = None
        self.cover_url = None
        self.cover_id = None
        self.goodreads_url = None
        self.goodreads_id = None
        self.oceanofpdf_url = None
        self.oceanofpdf_has_epub = True
        self.file_name = None
        self.file_path = None
        self.current_directory = None

    def __str__(self):
        return f"{self.title} By {self.author}"

    def display_book(self, index, total_results):
        output = f" - Result {index + 1} Of {total_results}:\n\n"
        output += f" * Book Title: {self.title}\n\n"
        output += f" * Book Author: {self.author}\n\n"

        if self.series:
            output += f" * Series: {self.series}"

        if self.series_index:
            output += f", Book #{self.series_index}\n\n"

        ui.update_image(image_data=self.cover)

        return output

    def get_oceanofpdf_search_data(self, result):
        result_data = result.get_attribute("outerHTML")
        soup = BeautifulSoup(result_data, "html.parser")

        self.title = soup.select(".entry-title-link")[0].text.strip()
        self.author = (
            str(soup.select(".postmetainfo")[0])
            .split("</strong>")[1]
            .split("<br/>")[0]
        )
        self.cover_url = re.sub(
            r"-\d+x\d+", "", soup.select(".post-image")[0]["src"]
        )
        self.cover = requests.get(
            self.cover_url, stream=True, headers=C.HEADERS
        ).content
        self.oceanofpdf_url = soup.select(".entry-title-link")[0]["href"]
        self.oceanofpdf_has_epub = (
            True if "epub" in re.split(r"[/-]", self.oceanofpdf_url) else False
        )

    def get_goodreads_search_data(self, result):
        result_data = result.get_attribute("outerHTML")
        soup = BeautifulSoup(result_data, "html.parser")

        self.title = soup.select(".bookTitle")[0].text.strip()
        self.author = soup.select(".authorName")[0].text.strip()

        patterns = [
            r"\(([^)]+),\s*#?\d+(\.\d+)?\)",  # (Series Name, #1) (Series Name, 1) (Series Name, 1.5)
            r"\(([^)]+)\s*#?\d+(\.\d+)?\)",  # (Series Name #1) (Series Name 1) (Series Name 1.5)
            r"\(([^)]+),\s*Book\s*#?\d+(\.\d+)?\)",  # (Series Name, Book #1) (Series Name, Book 1) (Series Name, Book 1.5)
            r"\(([^)]+)\s*Book\s*#?\d+(\.\d+)?\)",  # (Series Name Book #1) (Series Name Book 1) (Series Name Book 1.5)
        ]

        for pattern in patterns:
            match = re.search(pattern, self.title)
            if match:
                self.series = match.group(1).strip()

                series_index_match = re.search(r"\d+(\.\d+)?", match.group(0))
                self.series_index = (
                    float(series_index_match.group(0))
                    if series_index_match
                    else None
                )

                self.title = re.sub(pattern, "", self.title).strip()
                break

        self.goodreads_id = re.split(
            r"/|\.|-", soup.select(".bookTitle")[0]["href"]
        )[3]
        self.goodreads_url = (
            C.GOOD_READS_URL.replace("/search?q=", "")
            + "/book/show/"
            + self.goodreads_id
        )
        response = requests.get(self.goodreads_url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            self.cover_url = soup.select(".BookCover__image")[0].select("img")[
                0
            ]["src"]
            self.cover = requests.get(self.cover_url, stream=True).content

    def get_file_data(self, file):
        meta = ebookmeta.get_metadata(file)
        book = epubfile.Epub(file)

        self.title = meta.title
        self.author = meta.author_list_to_string()
        self.series = meta.series if meta.series else None
        self.series_index = meta.series_index if meta.series_index else None
        self.release_data = meta.publish_info if meta.publish_info else None

        cover_id = self.get_cover_id(book)
        self.cover_id = cover_id if cover_id else None
        self.cover = book.read_file(cover_id) if cover_id else None

        goodreads_id = file.split(" - ")[0]
        self.goodreads_id = goodreads_id if goodreads_id.isdigit() else None

        self.file_name = file.split("\\")[-1]
        self.file_path = file
        self.current_directory = self.file_path.replace(self.file_name, "")

    def get_cover_id(self, book):
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

            display_label(
                " # Cover Tag Could Not Be Found!\n - Please Check Terminal Log For Possible Tags\n - Please Submit These And Epub File On Github For Fixes",
                True,
            )
            return None

        return cover_id

    def update_file_path(self):
        self.file_path = os.path.join(self.current_directory, self.file_name)

    def override_book(self, book):
        attributes = [
            attr
            for attr in dir(book)
            if not callable(getattr(book, attr)) and not attr.startswith("__")
        ]

        for attr in attributes:
            current_value = getattr(self, attr)
            new_value = getattr(book, attr)
            setattr(
                self,
                attr,
                new_value if new_value is not None else current_value,
            )


class C:
    CURRENT_FOLDER = os.getcwd()
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/538.39 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    SOURCE_FOLDER = os.path.join(CURRENT_FOLDER, "Source")
    CHROME_PROFILE = os.path.join(CURRENT_FOLDER, "Chrome Profile")
    COMPLETED_FOLDER = os.path.join(CURRENT_FOLDER, "Completed")
    IN_PROGRESS_FOLDER = os.path.join(CURRENT_FOLDER, "In Progress")
    ERRORED_FOLDER = os.path.join(CURRENT_FOLDER, "Errored")
    ARCHIVE_FOLDER = os.path.join(CURRENT_FOLDER, "Archive")
    STRING_TO_REMOVE = "OceanofPDF.com"
    GOOD_READS_URL = "https://www.goodreads.com/search?q="
    GOOD_READS_DEFAULT_IMAGE = (
        "https://dryofg8nmyqjw.cloudfront.net/images/no-cover.png"
    )
    OCEANOFPDF_URL = "https://oceanofpdf.com/?s="
    DOWNLOAD_STAGES = 5
    PROCESS_STAGES = 9
    UPLOAD_STAGES = 8
    GOOD_READS_STEPS = 10


# endregion


# region Generic Helpers
def setup():
    ui.config(ui.top_frame.download_btn, command=download_new_book)
    ui.config(ui.top_frame.process_btn, command=process_files)
    ui.config(ui.top_frame.upload_btn, command=upload_books)

    check_folders()
    check_files()


def check_running_state():
    if not ui.is_running:
        sys.exit()


# endregion


# region Net Helpers
def fix_query(input_string):
    if not input_string:
        return False

    replacements = [f"_{C.STRING_TO_REMOVE}_", "-", "_", "(", ")", ".epub"]
    temp_string = input_string

    for part in replacements:
        temp_string = temp_string.replace(part, " ")

    query_normal = " ".join(temp_string.split())
    query = "+".join(temp_string.split())

    return [query, query_normal]


# endregion


# region File / Folder Helpers
def check_folders():
    thread = threading.Thread(target=check_folders_worker, daemon=True)
    thread.start()


def check_folders_worker():
    folders = [
        C.SOURCE_FOLDER,
        C.COMPLETED_FOLDER,
        C.IN_PROGRESS_FOLDER,
        C.ERRORED_FOLDER,
        C.ARCHIVE_FOLDER,
    ]

    for folder in folders:
        if not os.path.exists(folder):
            os.mkdir(folder)


def check_files():
    thread = threading.Thread(target=check_files_worker, daemon=True)
    thread.start()


def check_files_worker():
    source_files = [
        f for f in os.listdir(C.SOURCE_FOLDER) if f.endswith(".epub")
    ]
    completed_files = [
        f for f in os.listdir(C.COMPLETED_FOLDER) if f.endswith(".epub")
    ]

    ui.config(
        ui.top_frame.process_btn,
        state=("normal" if source_files else "disabled"),
    )
    ui.config(
        ui.top_frame.upload_btn,
        state=("normal" if completed_files else "disabled"),
    )


def get_folder_name(folder):
    return folder.split("\\")[-1]


def check_file_in_folder(file_name, directory):
    if os.path.exists(os.path.join(directory, file_name)):
        subtask = display_label(" # File Already Exists In Folder!", True)

        if input_confirm("Do You Want To Replace This File?"):
            os.remove(os.path.join(directory, file_name))
        else:
            file_counter = 1
            temp_name = file_name

            while os.path.exists(os.path.join(directory, temp_name)):
                temp_name = temp_name.replace(".epub", "")
                end_chars = temp_name.split(" ")[-1]

                if re.search(r"\(\d+\)", end_chars):
                    temp_name = re.sub(r" \(\d+\)", "", temp_name)

                temp_name = f"{temp_name} ({file_counter}).epub"
                file_counter += 1

            file_name = temp_name

        ui.destroy(subtask)

    return file_name


def move_file(file_name, source, destination, copy=False):
    mode = "Copied" if copy else "Moved"
    mode_during = "Copying" if copy else "Moving"
    subtask = display_label(
        f" - {mode_during} {file_name} To {get_folder_name(destination)}..."
    )

    new_file_name = check_file_in_folder(file_name, destination)
    file_paths = (
        os.path.join(source, file_name),
        os.path.join(destination, new_file_name),
    )

    if copy:
        shutil.copy(file_paths[0], file_paths[1])
    else:
        shutil.move(file_paths[0], file_paths[1])

    update_label(
        subtask,
        f" - {new_file_name} {mode} To {get_folder_name(destination)}!",
    )

    return new_file_name, destination


# endregion


# region UI Helpers
def display_label(text="", error=False):
    label = Label(
        ui.middle_frame.content_window,
        text=text,
        style="Red.TLabel" if error else "TLabel",
    )
    ui.pack(label)

    return label


def update_label(source_label, text="", error=False):
    ui.config(
        source_label, text=text, style="Red.TLabel" if error else "TLabel"
    )


# endregion


# region Input Helpers
def wait_for_input(input):
    while True:
        check_running_state()

        if input.get():
            break
        else:
            sleep(0.1)


def input_confirm(
    text="Are You Sure?",
    true_text="Yes",
    false_text="No",
    true_only=False,
    check_false=False,
):
    text = f"\n{text}"
    user_action = StringVar()

    ui.config(
        ui.bottom_frame.true_btn,
        command=lambda: user_action.set(True),
        text=true_text,
    )
    ui.config(
        ui.bottom_frame.false_btn,
        command=lambda: user_action.set(False),
        text=false_text,
        state="disabled" if true_only else None,
    )

    confirm_label = display_label(text)

    ui.bottom_frame.hide()
    ui.bottom_frame.show_confirm_input()

    wait_for_input(user_action)

    ui.destroy(confirm_label)
    ui.bottom_frame.hide()

    response = bool(int(user_action.get()))

    if check_false and not response:
        response = not input_confirm()

    return response


def input_text(text="", label_text="Search Term:", btn_text="Enter"):
    text = f"\n{text}"
    user_input = StringVar()

    ui.config(ui.bottom_frame.text_input_label, text=label_text)
    ui.config(ui.bottom_frame.text_input_btn, text=btn_text)

    text_label = display_label(text)

    ui.bottom_frame.hide()
    ui.bottom_frame.show_text_input()

    ui.config(
        ui.bottom_frame.text_input_btn,
        command=lambda: user_input.set(
            ui.bottom_frame.text_input.get()
            if ui.bottom_frame.text_input.get()
            else "^"
        ),
    )

    wait_for_input(user_input)

    ui.bottom_frame.text_input.delete(0, END)

    ui.destroy(text_label)
    ui.bottom_frame.hide()

    if user_input.get() == "^":
        if input_confirm():
            return False

    return user_input.get()


def input_nav(
    manual_text="Manual",
    prev_text="Prev",
    select_text="Select",
    next_text="Next",
    skip_text="Skip",
    disable_manual=False,
    disable_prev=False,
    disable_select=False,
    disable_next=False,
    disable_skip=False,
):
    state = ["normal", "disabled"]
    user_action = StringVar()

    ui.config(
        ui.bottom_frame.manual_btn,
        text=manual_text,
        state=state[1] if disable_manual else state[0],
        command=lambda: user_action.set("manual"),
    )
    ui.config(
        ui.bottom_frame.prev_btn,
        text=prev_text,
        state=state[1] if disable_prev else state[0],
        command=lambda: user_action.set("prev"),
    )
    ui.config(
        ui.bottom_frame.select_btn,
        text=select_text,
        state=state[1] if disable_select else state[0],
        command=lambda: user_action.set("/"),
    )
    ui.config(
        ui.bottom_frame.next_btn,
        text=next_text,
        state=state[1] if disable_next else state[0],
        command=lambda: user_action.set("next"),
    )
    ui.config(
        ui.bottom_frame.skip_btn,
        text=skip_text,
        state=state[1] if disable_skip else state[0],
        command=lambda: user_action.set(" "),
    )

    ui.bottom_frame.hide()
    ui.bottom_frame.show_nav_input()

    wait_for_input(user_action)

    ui.bottom_frame.hide()

    if user_action.get() == " ":
        if input_confirm():
            return False

    if user_action.get() == "/":
        return True

    return user_action.get()


# endregion


# region Selenium Helpers
def create_chrome_driver():
    subtask = display_label(" - Creating Automated Chrome Window...")
    options = uc.ChromeOptions()

    preferences_file = os.path.join(C.CHROME_PROFILE, "Default\\Preferences")
    if os.path.exists(preferences_file):
        os.remove(preferences_file)

    options.add_argument(f"--user-data-dir={C.CHROME_PROFILE}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--disable-notifications")
    options.add_experimental_option(
        "prefs", {"download.default_directory": C.SOURCE_FOLDER}
    )
    web_driver = uc.Chrome(options=options)
    web_driver.minimize_window()

    update_label(subtask, " - Chrome Window Created!")

    return web_driver


def focus_driver(web_driver):
    web_driver.execute_script("window.focus();")
    web_driver.set_window_size(width=100, height=400)


def find_element(web_driver, element, wait_time=10, click=False):
    time_waited = 0

    while time_waited <= wait_time:
        check_running_state()

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


def find_elements(web_driver, element, wait_time=10):
    time_waited = 0

    while time_waited <= wait_time:
        check_running_state()

        try:
            found_elements = WebDriverWait(web_driver, 1).until(
                EC.presence_of_all_elements_located(element)
            )
            return found_elements
        except:
            time_waited += 1

    return False


def clear_driver_tabs(web_driver):
    subtask = display_label(" - Clearing Extra Tabs...")
    focus_driver(web_driver)

    while len(web_driver.window_handles) > 1:
        web_driver.close()
        web_driver.switch_to.window(web_driver.window_handles[0])

    web_driver.minimize_window()
    update_label(subtask, " - Extra Tabs Cleared!")


# endregion


# region Generic Task Function Helpers
def end_task_function(web_driver):
    display_label()
    web_driver.quit()
    ui.top_frame.hide()
    ui.top_frame.show_task_btns()
    check_files()


def archive_files():
    files = [f for f in os.listdir(C.COMPLETED_FOLDER) if f.endswith(".epub")]
    subtask = display_label(" - Archiving Files...")

    for file_name in files:
        subtask_log = display_label(f" * {file_name}")
        if input_confirm("Would You Like To Archive This Book?"):
            move_file(file_name, C.COMPLETED_FOLDER, C.ARCHIVE_FOLDER)
            ui.destroy(subtask_log)
            continue

        update_label(subtask_log, f" - {file_name} Skipped!")

    update_label(subtask, " - Archiving Finished!")
    return True


def search_site_for_books(web_driver, label, query, url, element):
    focus_driver(web_driver)
    web_driver.get(f"{url}{query[0]}")

    results = find_elements(web_driver, element)
    web_driver.minimize_window()

    if not results:
        update_label(label, f" # No Results For {query[1]}!", True)
        return False

    return results


def process_search_results(results, goodreads=False, oceanofpdf=False):
    books = []
    loading_label = display_label("Loading...")

    for result in results:
        check_running_state()

        book = Book()
        book.get_goodreads_search_data(result) if goodreads else None
        book.get_oceanofpdf_search_data(result) if oceanofpdf else None
        books.append(book)

    ui.destroy(loading_label)
    return books


def book_results_menu(books, results_count):
    current_index = 0

    while True:
        check_running_state()

        book_result = display_label()
        update_label(
            book_result,
            books[current_index].display_book(current_index, results_count),
        )

        user_action = input_nav(
            manual_text="New Search",
            skip_text="Cancel",
            select_text=(
                "Select"
                if books[current_index].oceanofpdf_has_epub
                else "NO EPUB FOUND"
            ),
            disable_prev=False if current_index > 0 else True,
            disable_select=not books[current_index].oceanofpdf_has_epub,
            disable_next=False if current_index + 1 < results_count else True,
        )
        ui.destroy(book_result)

        match (user_action):
            case "next":
                current_index += 1
            case "prev":
                current_index += -1
            case _:
                return user_action, current_index


# endregion


# region OceanOfPDF Download Helpers
def download_oceanofpdf_epub(web_driver, book):
    subtask = display_label(f" - Downloading {book.title}...")

    focus_driver(web_driver)
    web_driver.get(book.oceanofpdf_url)

    if not find_element(
        web_driver,
        (
            By.XPATH,
            "//input[@src='https://media.oceanofpdf.com/epub-button.jpg']",
        ),
        click=True,
    ):
        web_driver.minimize_window()
        update_label(
            subtask,
            " # Failed To Find Download Button! - Blame OceanOfPDF!",
            True,
        )
        return False

    web_driver.minimize_window()

    if not wait_for_download(C.SOURCE_FOLDER):
        return False

    update_label(subtask, f" - {book.title} Downloaded!")
    return True


def wait_for_download(source_folder):
    time_waited = 0
    old_files_count = len(
        [f for f in os.listdir(source_folder) if f.endswith(".epub")]
    )

    while True:
        check_running_state()

        new_files_count = len(
            [f for f in os.listdir(source_folder) if f.endswith(".epub")]
        )

        if new_files_count > old_files_count:
            return True

        sleep(1)
        time_waited += 1

        if time_waited == 30:
            time_waited = 0
            if not input_confirm(
                "Download May Have Failed!\n - Please Check Download Progress In Chrome Window!"
            ):
                display_label(" # Download Has Failed!", True)
                return False


# endregion


# region Process Files Helpers
def clean_book(book):
    subtask = display_label(" - Cleaning Book Content...")
    book = epubfile.Epub(book.file_path)

    for page in book.get_texts():
        soup = book.read_file(page)
        soup = soup.replace(C.STRING_TO_REMOVE, "")
        book.write_file(page, soup)

    update_label(subtask, " - Book Content Cleaned!")
    return True


def get_metadata_from_goodreads(web_driver, book):
    query = fix_query(book.title)
    subtask = display_label(f" - Searching {query[1]} On GoodReads...")

    while True:
        check_running_state()

        current_index = 0
        books = []

        if not query:
            update_label(subtask, f" # Metadata Search Skipped!", True)
            return book

        update_label(subtask, f" - Searching {query[1]} On GoodReads...")
        results = search_site_for_books(
            web_driver, subtask, query, C.GOOD_READS_URL, (By.TAG_NAME, "tr")
        )
        ui.top_frame.update_progress_bar()

        if results:
            books = process_search_results(results, goodreads=True)
            ui.top_frame.update_progress_bar()

            user_action, current_index = book_results_menu(books, len(books))
        else:
            if input_confirm("Would You Like To Search Manually?"):
                user_action = "manual"
            else:
                user_action = False

        if user_action == "manual":
            update_label(subtask, f" - Manual GoodReads Search:")
            query_input = input_text(
                text="Please Enter Your Search Term\n - (Leave Blank To Skip)"
            )

            if not query_input:
                break
            query = fix_query(query_input)
            continue

        if user_action == True:
            update_label(subtask, " - GoodReads Search Completed!")
            book.override_book(books[current_index])
            break

        if not user_action:
            update_label(subtask, f" # Metadata Search Skipped!", True)
            break

    return book


def get_cover_from_user(label):
    while True:
        url = input_text(
            "Please Enter An Image URL\n - (Leave Black To Use Default)",
            label_text="URL:",
        )

        if not url:
            url = C.GOOD_READS_DEFAULT_IMAGE

        if not url.lower().endswith((".jpg", ".jpeg", ".png")):
            update_label(
                label, " # Not Accepted Format!\n - Must Be JPG Or PNG!", True
            )
            continue

        response = requests.get(url, stream=True)

        if not response.status_code == 200:
            update_label(label, " # Image Not Found, Please Try Again!", True)
            continue

        return url, response.content


def select_cover(book):
    subtask = display_label(f" - Confirming Cover Image...")

    if not book.cover:
        update_label(
            subtask, " # Skipping Cover Image!\n - Can't Access Book's Cover!"
        )
        return book

    subtask_log = display_label()

    if book.cover_url == C.GOOD_READS_DEFAULT_IMAGE and book.cover_id:
        update_label(
            subtask_log, " - Missing Book Cover!, Pulling From EPUB..."
        )
        ui.update_image(image_data=book.cover)

    while True:
        if not input_confirm("Do You Want To Use This Cover?"):
            book.cover_url, book.cover = get_cover_from_user(subtask_log)

            update_label(subtask, " - Confirming Cover Image...")
            ui.update_image(image_data=book.cover)
            continue

        break

    update_label(subtask, " - Cover Image Confirmed!")
    ui.destroy(subtask_log)
    return book


def update_metadata(book):
    subtask = display_label(" - Updating Book Metadata...")
    subtask_log = display_label(" * Getting Data From Book...")

    meta = ebookmeta.get_metadata(book.file_path)

    meta.title = book.title
    update_label(subtask_log, " * Book Title Updated!")

    meta.set_author_list_from_string(book.author)
    update_label(subtask_log, " * Book Author Updated!")

    meta.series = book.series
    update_label(subtask_log, " * Book Series Updated!")

    meta.series_index = book.series_index
    update_label(subtask_log, " * Book Series Index Updated!")

    meta.publish_info = book.release_data
    update_label(subtask_log, " * Release Date Updated!")

    ebookmeta.set_metadata(book.file_path, meta)
    if book.cover:
        book_file = epubfile.Epub(book.file_path)
        book_file.write_file(book.cover_id, book.cover)
        book_file.save(book.file_path)
        update_label(subtask_log, " * Cover Updated!")
    ui.destroy(subtask_log)

    update_label(subtask, " - Book Metadata Updated!")


def delete_source_files(file_name):
    subtask = display_label(" - Deleting Source File...")

    if input_confirm("Would You Like To Delete The Source File?"):
        if os.path.exists(os.path.join(C.SOURCE_FOLDER, file_name)):
            os.remove(os.path.join(C.SOURCE_FOLDER, file_name))
            update_label(subtask, " - Source File Deleted!")
        else:
            display_label(
                f" # {file_name} Not Found In {C.SOURCE_FOLDER}!", True
            )
            return False
    else:
        update_label(subtask, " - Source File Not Deleted!")

    return True


def rename_file(book):
    subtask = display_label(" - Renaming EPUB File...")

    new_name = f"{book.title}"
    new_name += (
        f" ({book.series}, #{book.series_index})" if book.series else ""
    )
    new_name += " - " + book.author.replace(", ", " - ")
    new_name = new_name.replace(":", "") + ".epub"
    if not new_name == book.file_name:
        new_name = check_file_in_folder(new_name, book.current_directory)

        os.rename(
            os.path.join(book.current_directory, book.file_name),
            os.path.join(book.current_directory, new_name),
        )

        book.file_name = new_name
        book.update_file_path()

    update_label(subtask, f" - EPUB File Renamed: {new_name}")
    return book


# endregion


# region Google Play Books Upload Helpers
def check_play_books_logged_in(web_driver):
    subtask = display_label(" - Checking If You Are Logged In...")

    while True:
        web_driver.get("https://play.google.com/books/uploads")
        element = (By.XPATH, "//span[text()='Sign in']")

        if not find_element(web_driver, element, wait_time=2, click=True):
            update_label(subtask, " - Logged In!")
            return True

        subtask_label = display_label("Not Logged In, Please Login Now.", True)
        web_driver.maximize_window()
        response = input_confirm(
            text="Please Click Done When You Have Logged In.",
            true_text="Done",
            false_text="Cancel",
        )
        focus_driver()
        web_driver.minimize_window()
        ui.destroy(subtask_label)

        if not response:
            update_label(subtask, " - Login Cancelled!", True)
            return False

        return True


def get_files_for_upload(files):
    file_paths = []
    subtask = display_label(" - Collecting EPUB Files...")

    for file_name in files:
        ui.top_frame.update_progress_bar()
        subtask_log = display_label(f"\n * {file_name}")
        if input_confirm("Would You Like To Upload This File?"):
            file_paths.append(os.path.join(C.COMPLETED_FOLDER, file_name))
            update_label(subtask_log, f" - {file_name} Added To Queue")
            continue

        update_label(subtask_log, f" - {file_name} Skipped!")

    if len(file_paths) == 0:
        update_label(subtask, " # All Files Skipped, Nothing To Upload!", True)
        return False

    update_label(subtask, " - EPUB Files Collected!")
    return file_paths


def upload_to_play_books(web_driver, files):
    subtask = display_label(" - Uploading Files To Play Books...")

    focus_driver(web_driver)
    find_element(
        web_driver,
        (By.XPATH, "//span[text()='\n      Upload files']"),
        click=True,
    )
    iframe = find_element(web_driver, (By.ID, ":0.contentEl"))

    if iframe:
        iframe = find_element(iframe, (By.TAG_NAME, "iframe"))

        if iframe:
            web_driver.switch_to.frame(iframe)
            file_input = find_element(
                web_driver, (By.XPATH, "//input[@type='file']")
            )

            if file_input:
                file_paths = "\n".join(files)
                file_input.send_keys(file_paths)
    else:
        update_label(" # Unable To Upload Files!")
        return False

    web_driver.switch_to.default_content()

    update_label(subtask, " - Files Added To Play Books Upload Queue!")
    return True


def wait_for_play_books_upload(web_driver):
    subtask = display_label(" - Waiting For Upload")
    time_waited = 0

    while True:
        tracker = find_element(web_driver, (By.ID, ":0.contentEl"))

        if not tracker:
            break

        time_waited += 1
        sleep(1)

        if time_waited == 30:
            time_waited = 0
            if not input_confirm(
                "Upload May Have Failed!\n - Please Check Upload Progress In Chrome Window!\n - Have The Uploads Finished?"
            ):
                display_label(" # Upload Has Failed!", True)
                return False

    web_driver.minimize_window()
    update_label(subtask, " - Books Uploaded!")
    return True


# endregion


# region Task Worker Functions
def download_new_book_worker():
    task_label = display_label("Downloading New Books...")
    web_driver = create_chrome_driver()
    display_label()

    def download_cancelled():
        update_label(task_label, " # File Downloads Cancelled!", True)
        end_task_function(web_driver)

    def downloads_finished():
        update_label(task_label, "File Downloads Finished!")
        end_task_function(web_driver)

    def process_download():
        update_label(task, f" - Found Result For {query[1]}!")
        download_oceanofpdf_epub(web_driver, books[current_index])
        ui.top_frame.update_progress_bar()

        clear_driver_tabs(web_driver)
        display_label()
        ui.top_frame.update_progress_bar()

    while True:
        check_running_state()

        current_index = 0
        books = []

        ui.update_image(ui.DEFAULT_IMAGE_URL)
        ui.top_frame.hide()
        ui.top_frame.show_progress_bar("Downloading New Book:")
        ui.config(ui.top_frame.progress_bar, maximum=C.DOWNLOAD_STAGES)

        query = fix_query(
            input_text(
                "What Book Would You Like To Search For?\n - (Leave Blank To Cancel)",
                label_text="Search:",
            )
        )

        if not query:
            download_cancelled()
            return
        ui.top_frame.update_progress_bar()

        task = display_label(f" - Searching For {query[1]}...")
        results = search_site_for_books(
            web_driver, task, query, C.OCEANOFPDF_URL, (By.TAG_NAME, "article")
        )
        ui.top_frame.update_progress_bar()

        if results:
            update_label(task, f" - {len(results)} Results For {query[1]}")
            books = process_search_results(results, oceanofpdf=True)
            ui.top_frame.update_progress_bar()

            user_action, current_index = book_results_menu(books, len(books))
        else:
            if input_confirm("Would You Like To Search Manually?"):
                user_action = "manual"
            else:
                user_action = False

        if user_action == "manual":
            update_label(task, " - Starting New Search...")
            continue

        if user_action == True:
            process_download()

            if not input_confirm("Do You Want To Search For Another Book?"):
                downloads_finished()
                return
            continue

        if not user_action:
            download_cancelled()
            return


def process_files_worker():
    files = [f for f in os.listdir(C.SOURCE_FOLDER) if f.endswith(".epub")]
    ui.config(ui.top_frame.progress_bar, maximum=C.PROCESS_STAGES * len(files))
    task_label = display_label(f"Processing {len(files)} Files...")
    web_driver = create_chrome_driver()
    display_label()

    ui.top_frame.hide()
    ui.top_frame.show_progress_bar("Processing Files:")

    for index, file_name in enumerate(files):
        task = display_label(f"Would You Like To Process This File?")
        source_file_name = file_name

        if not input_confirm(file_name):
            update_label(task, f" # File: {file_name} Skipped!", True)
            display_label()
            ui.top_frame.update_progress_bar(
                C.PROCESS_STAGES * (index + 1), True
            )
            continue

        update_label(task, f"Processing File: {file_name}...")

        book = Book()
        book.get_file_data(os.path.join(C.SOURCE_FOLDER, file_name))

        try:

            book.file_name, book.current_directory = move_file(
                book.file_name,
                book.current_directory,
                C.IN_PROGRESS_FOLDER,
                True,
            )
            book.update_file_path()
            ui.top_frame.update_progress_bar()

            clean_book(book)
            ui.top_frame.update_progress_bar()

            book = get_metadata_from_goodreads(web_driver, book)
            ui.top_frame.update_progress_bar()

            book = select_cover(book)
            ui.top_frame.update_progress_bar()

            update_metadata(book)
            ui.top_frame.update_progress_bar()

            book = rename_file(book)
            book.update_file_path()
            ui.top_frame.update_progress_bar()

            book.file_name, book.current_directory, move_file(
                book.file_name, book.current_directory, C.COMPLETED_FOLDER
            )
            book.update_file_path()
            ui.top_frame.update_progress_bar()

            delete_source_files(source_file_name)
            ui.top_frame.update_progress_bar()

            update_label(task, f"Processing File: {file_name}, Done!")
            ui.top_frame.update_progress_bar()

            display_label()
            ui.update_image(ui.DEFAULT_IMAGE_URL)
        except Exception as e:
            update_label(task, f"Processing File: {file_name} - FAILED!", True)
            ui.top_frame.update_progress_bar(
                C.PROCESS_STAGES * (index + 1), True
            )
            tb = traceback.format_exc()

            last_line = tb.strip().split("\n")[-1]

            display_label()
            display_label(f"Error Details: {last_line}", True)
            move_file(book.file_name, book.current_directory, C.ERRORED_FOLDER)
            display_label()

    update_label(task_label, f"Processing {len(files)} Files, Done!")
    end_task_function(web_driver)


def upload_books_worker():
    ui.top_frame.hide()
    ui.top_frame.show_progress_bar("Uploading Files:")

    files = [f for f in os.listdir(C.COMPLETED_FOLDER) if f.endswith(".epub")]
    task_label = display_label(f"Uploading {len(files)} Files...")
    ui.config(
        ui.top_frame.progress_bar, maximum=C.UPLOAD_STAGES + (len(files) * 2)
    )

    def upload_cancelled():
        update_label(task_label, " # File Upload Cancelled!", True)
        end_task_function(web_driver)

    web_driver = create_chrome_driver()
    display_label()
    ui.top_frame.update_progress_bar()

    if not check_play_books_logged_in(web_driver):
        upload_cancelled()
        return
    ui.top_frame.update_progress_bar()

    epubs_for_upload = get_files_for_upload(files)
    if not epubs_for_upload:
        upload_cancelled()
        return
    ui.top_frame.update_progress_bar()

    if not upload_to_play_books(web_driver, epubs_for_upload):
        upload_cancelled()
        return
    ui.top_frame.update_progress_bar()

    wait_for_play_books_upload(web_driver)
    ui.top_frame.update_progress_bar()

    archive_files()
    ui.top_frame.update_progress_bar()

    update_label(task_label, f"Uploading {len(files)} Files, Done!")
    ui.top_frame.update_progress_bar()
    end_task_function(web_driver)


# endregion


# region Task Functions
def download_new_book():
    thread = threading.Thread(target=download_new_book_worker, daemon=True)
    thread.start()


def process_files():
    thread = threading.Thread(target=process_files_worker, daemon=True)
    thread.start()
    pass


def upload_books():
    thread = threading.Thread(target=upload_books_worker, daemon=True)
    thread.start()


# endregion


ui = Window()
setup()
ui.root.mainloop()
