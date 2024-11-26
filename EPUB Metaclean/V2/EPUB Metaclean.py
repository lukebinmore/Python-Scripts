import os
from rich.console import Console
from rich.prompt import Prompt, Confirm
import epubfile
import warnings
import ebookmeta
import requests
from bs4 import BeautifulSoup
import textwrap
import shutil
from PIL import Image, ImageTk
import tkinter as tk
import time
import traceback


class ImageViewer:
    def __init__(self):
        self.root = None
        self.label = None

    def IsWindowOpen(self):
        if self.root:
            try:
                return self.root.winfo_exists()
            except tk.TclError:
                return False
        return False

    def OpenWindow(self):
        if not self.IsWindowOpen():
            self.root = tk.Tk()
            self.label = tk.Label(self.root)
            self.label.pack()

    def ResizeImage(self, img):
        img.thumbnail((500, 1000), Image.Resampling.LANCZOS)
        return img

    def ShowCover(self, image_path):
        self.OpenWindow()
        img = Image.open(image_path)
        img = self.ResizeImage(img)
        img_tk = ImageTk.PhotoImage(img)
        self.label.config(image=img_tk)
        self.label.image = img_tk
        self.root.title(image_path)


console = Console(style="Green")
viewer = ImageViewer()
currentFolder = os.getcwd() + "\\"
sourceFolder = currentFolder + "Source\\"
completedFolder = currentFolder + "Completed\\"
inProgressFolder = currentFolder + "In Progress\\"
imagesFolder = currentFolder + "Images\\"
erroredFolder = currentFolder + "Errored\\"
stringToRemove = "OceanofPDF.com"


def ClearLine(lines=1):
    for i in range(lines):
        print("\r\033[1A\033[1G\033[K", end="")


def StringLines(string_to_calculate):
    screen_width = shutil.get_terminal_size().columns
    lines = string_to_calculate.split("\n")
    total_lines = 0
    for line in lines:
        total_lines += len(line) // screen_width

    return total_lines


def SPrint(input, lines=0):
    ClearLine(lines) if lines > 0 else None
    console.print(
        textwrap.shorten(
            input,
            width=shutil.get_terminal_size().columns - 10,
            placeholder="...",
        )
    )


def FitToScreen(input):
    return textwrap.shorten(
        input, width=shutil.get_terminal_size().columns - 10, placeholder="..."
    )


def GetFolderName(folder):
    return folder.split("\\")[-2]


def GetResponse(url, query_parameters={}):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/538.39 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    while True:
        try:
            response = requests.get(
                url, query_parameters, headers=headers, timeout=15
            )
            return response
        except requests.exceptions.Timeout:
            time.sleep(1)
        except Exception as e:
            return requests.Response()


def Start():
    warnings.filterwarnings("ignore")
    console.rule("#### OceanOfPDF EPUB Cleaner ####\n", style="bold")
    console.print("\033[92m")


def CheckFolders():
    SPrint("Checking Folders:")
    folders = [
        sourceFolder,
        completedFolder,
        inProgressFolder,
        imagesFolder,
        erroredFolder,
    ]
    for folder in folders:
        SPrint(f"Creating [white]{GetFolderName(folder)}[/white]...")
        if not os.path.exists(folder):
            os.makedirs(folder)
        SPrint(f"Creating {GetFolderName(folder)}, Done!", 1)
    SPrint("All Folders Ready!")
    console.print("")


def MoveFile(fileName, source, destination, copy=False):
    SPrint(f"Moving [white]{fileName}[/white]...")
    SPrint(
        f"Moving from: {GetFolderName(source)} To {GetFolderName(destination)}..."
    )
    if copy:
        shutil.copy(source + fileName, destination + fileName)
    else:
        shutil.move(source + fileName, destination + fileName)
    SPrint(f"Moving {fileName}, Done!", 2)
    return destination


def CleanBook(fileName, file):
    book = epubfile.Epub(file)
    SPrint(f"Cleaning [white]{fileName}[/white]...")

    for page in book.get_texts():
        soup = book.read_file(page)
        soup = soup.replace(stringToRemove, "")
        book.write_file(page, soup)

    book.save(file)
    SPrint(f"Cleaning {fileName}, Done!", 1)


def SearchBook(fileName):
    query = "+".join(
        fileName.replace(f"_{stringToRemove}_", " ")
        .replace("-", " ")
        .replace("_", " ")
        .replace("(", " ")
        .replace(")", " ")
        .replace(".epub", "")
        .split()
    )
    while True:
        query_normal = query.replace("+", " ")
        SPrint(f"Searching GoodReads For {query_normal}...")
        url = f"https://www.goodreads.com/search?q={query}"
        response = GetResponse(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            results = soup.select("tr")
            if results:
                SPrint(
                    f"{len(results)} Results For [white]{query_normal}:[/white]"
                )
                SPrint("- - Enter Different Search Term")
                SPrint("+ - Skip Book")
                for i in range(len(results)):
                    book_title = FitToScreen(
                        results[i].select(".bookTitle")[0].text.strip()
                    )
                    SPrint(f"{i} - {book_title}")
                selection = Prompt.ask(
                    "Please Select Book (Leave Blank For Default)",
                    default="0",
                )
                ClearLine(len(results) + 3)
                if selection == "+":
                    SPrint(f"[red]Skipping {fileName}![/red]", 2)
                    return False
                if selection == "-":
                    SPrint(f"Manual Search For [white]{fileName}[/white]", 1)
                    query = Prompt.ask(
                        f"Please Enter Search Term (Leave Blank To Skip)",
                        default="",
                    ).replace(" ", "+")
                    ClearLine(3)
                    if query == "":
                        SPrint(f"[red]Skipping {fileName}![/red]", 1)
                        return False
                    else:
                        continue
                selection = int(selection)
                book_title = (
                    results[selection].select(".bookTitle")[0].text.strip()
                )
                book_author = (
                    results[selection].select(".authorName")[0].text.strip()
                )
                book_url = str(
                    results[selection].select(".bookTitle")[0]["href"]
                )
                SPrint(f"Searching Goodreads For {book_title}, Done!", 2)
                return {
                    "Title": book_title,
                    "Author": book_author,
                    "URL": book_url,
                }


def GetCover(book_data):
    title = book_data["Title"]
    url = book_data["URL"]
    SPrint(f"Getting [white]{title}[/white] Cover...")
    url = "https://goodreads.com" + url.split(".")[0]
    response = GetResponse(url)
    if response.status_code == 200:
        image_url = (
            BeautifulSoup(response.content, "html.parser")
            .select(".BookCover__image")[0]
            .find("img", class_="ResponsiveImage")["src"]
        )
        default_image_url = image_url
        while True:
            SPrint(f"Downloading [white]{title}[/white] Cover...", 1)
            query_parameters = {"downloadformat": "jpg"}
            fileName = title + ".jpg"
            image_response = GetResponse(image_url, query_parameters)
            if image_response.status_code == 200:
                with open(imagesFolder + fileName, "wb") as img:
                    img.write(image_response.content)
                with Image.open(imagesFolder + fileName) as img:
                    img = img.convert("RGB")
                    img = img.resize([1600, 2560])
                    img.save(imagesFolder + fileName)
                viewer.ShowCover(imagesFolder + fileName)
                ClearLine()
                confirm_image = Confirm.ask(
                    f"Use This Book Cover?", default=True
                )
                if confirm_image:
                    SPrint(f"Getting {title} Cover, Done!", 1)
                    return fileName
            else:
                SPrint(f"[red]ERROR - Not An Image! - {image_url}", 1)
                input("Press Any Key To Enter A New URL...")
                ClearLine()

            SPrint(
                f"Please Enter Cover URL (Leave Blank For GoodReads Default):",
                1,
            )
            image_url = input("")
            ClearLine(StringLines(image_url) + 1)
            if image_url == "":
                image_url = default_image_url


def UpdateMetadata(fileName, file, book_data):
    SPrint(f"Updating Metadata For [white]{fileName}[/white]...")
    meta = ebookmeta.get_metadata(file)
    meta.title = book_data["Title"]
    meta.set_author_list_from_string(book_data["Author"])
    ebookmeta.set_metadata(file, meta)
    book = epubfile.Epub(file)
    cover_id = book.get_cover_image()
    with open(imagesFolder + book_data["Cover"], "rb") as img:
        img_data = img.read()
        book.write_file(cover_id, img_data)
    book.save(file)
    SPrint(f"Updating Metadata For {fileName}, Done!", 1)


def RenameFile(fileName, file, source):
    SPrint(f"Renaming [white]{fileName}[/white]...")
    meta = ebookmeta.get_metadata(file)
    new_name = meta.title
    new_name += " - "
    new_name += meta.author_list_to_string().replace(", ", " - ")
    new_name = new_name.replace(":", "")
    new_name += ".epub"
    os.rename(source + fileName, source + new_name)
    SPrint(f"Renaming {fileName}, Done!", 1)
    return new_name


def ClearFolders():
    while True:
        confirm_clear = Confirm.ask(
            "Have All Files Uploaded Successfully?", default=True
        )
        ClearLine()
        if confirm_clear:
            break

    SPrint("Clearing Folders:")
    folders = [sourceFolder, inProgressFolder, imagesFolder, erroredFolder]
    for folder in folders:
        SPrint(f"Deleting [white]{GetFolderName(folder)}[/white]...")
        if folder == erroredFolder:
            SPrint(f"Skipping Errored Folder, Contains Errored Files!", 1)
        else:
            shutil.rmtree(folder)
            SPrint(f"Deleting {GetFolderName(folder)}, Done!", 1)

    SPrint(f"Re-Creating [white]{sourceFolder}[/white]...")
    os.makedirs(sourceFolder)
    SPrint(f"Re-Creating {sourceFolder}, Done!", 1)
    SPrint("All Folders Cleared!")
    print("")


def End():
    console.print("All Files Have Been Cleaned!")
    input("Please press any key to close this window...")
    exit()


def Main():
    Start()
    CheckFolders()

    files = [f for f in os.listdir(sourceFolder) if f.endswith(".epub")]

    if not files:
        End()

    for fileName in files:
        try:
            SPrint(f"Working On {fileName}:")
            current_directory = MoveFile(
                fileName, sourceFolder, inProgressFolder, True
            )
            CleanBook(fileName, inProgressFolder + fileName)
            book_data = SearchBook(fileName)
            if not book_data:
                continue
            book_data["Cover"] = GetCover(book_data)
            UpdateMetadata(fileName, inProgressFolder + fileName, book_data)
            newFileName = RenameFile(
                fileName, inProgressFolder + fileName, inProgressFolder
            )
            current_directory = MoveFile(
                newFileName, inProgressFolder, completedFolder
            )
            SPrint(f"Working On {fileName}, Done!")

        except Exception as e:
            SPrint(f"[red]ERROR - {fileName}[/red]")
            tb = traceback.format_exc()
            last_line = tb.strip().split("\n")[-1]
            SPrint(f"[red]Error Details: {last_line}")
            MoveFile(fileName, current_directory, erroredFolder)

        console.print("")

    ClearFolders()
    End()


Main()
