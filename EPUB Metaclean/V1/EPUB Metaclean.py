import os
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.progress import Progress
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

console = Console(style="Green")
currentFolder = os.getcwd() + "\\"
toDoFolder = currentFolder + "To Do\\"
inProgressFolder = currentFolder + "In Progress\\"
doneFolder = currentFolder + "Done\\"
erroredFolder = currentFolder + "Errored\\"
stringToRemove = "OceanofPDF.com"


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


def ClearLine(lines=1):
    for i in range(lines):
        print("\r\033[1A\033[1G\033[K", end="")


def Start():
    warnings.filterwarnings("ignore")
    console.rule("#### OceanOfPDF EPUB Cleaner ####\n", style="bold")
    print("")


def CheckFolders():
    with Progress() as progress:
        task = progress.add_task("Creating Folders:", total=4)
        if not os.path.exists(toDoFolder):
            toDoTask = progress.add_task("Creating To Do Folder:", total=1)
            os.makedirs(toDoFolder)
            progress.update(toDoTask, advance=1)
            progress.update(task, advance=1)
        else:
            progress.update(task, advance=1)
        if not os.path.exists(inProgressFolder):
            inProgressTask = progress.add_task(
                "Creating In Progress Folder:", total=1
            )
            os.makedirs(inProgressFolder)
            progress.update(inProgressTask, advance=1)
            progress.update(task, advance=1)
        else:
            progress.update(task, advance=1)
        if not os.path.exists(doneFolder):
            doneTask = progress.add_task("Creating Done Folder:", total=1)
            os.makedirs(doneFolder)
            progress.update(doneTask, advance=1)
            progress.update(task, advance=1)
        else:
            progress.update(task, advance=1)
        if not os.path.exists(erroredFolder):
            errorTask = progress.add_task("Creating Errored Folder:", total=1)
            os.makedirs(erroredFolder)
            progress.update(errorTask, advance=1)
            progress.update(task, advance=1)
        else:
            progress.update(task, advance=1)
    console.print("All Folders Ready!\n")


def RenameFiles():
    files = [f for f in os.listdir(inProgressFolder) if f.endswith(".epub")]
    with Progress(console=console) as progress:
        if files:
            task = progress.add_task("Renaming EPUB Files:", total=len(files))
        else:
            task = progress.add_task("Renaming EPUB Files:", total=1)

        for fileName in files:
            try:
                file = inProgressFolder + fileName
                meta = ebookmeta.get_metadata(file)
                fileTask = progress.add_task(
                    f"Renaming {FitToScreen(fileName)}", total=3
                )
                new_name = meta.title
                new_name += " - "
                new_name += meta.author_list_to_string().replace(", ", " - ")
                new_name = new_name.replace(":", "")
                new_name += ".epub"
                progress.update(fileTask, advance=1)
                new_file_path = inProgressFolder + new_name
                progress.update(fileTask, advance=1)
                os.rename(file, new_file_path)
                progress.update(fileTask, advance=1)
            except KeyError as e:
                fileTask = progress.add_task(
                    f"Renaming {FitToScreen(fileName)}", total=len(files)
                )
            progress.update(task, advance=1)
        if not files:
            progress.update(task, completed=1)
    console.print("All Files Renamed!\n")


def MoveToInProgress():
    files = [f for f in os.listdir(toDoFolder) if f.endswith(".epub")]
    with Progress(console=console) as progress:
        if files:
            task = progress.add_task(
                "Collecting EPUB Files:", total=len(files)
            )
        else:
            task = progress.add_task("Collecting EPUB Files:", total=1)

        for fileName in files:
            fileTask = progress.add_task(
                f"Moving {FitToScreen(fileName)}", total=3
            )
            old_file_path = os.path.join(toDoFolder, fileName)
            progress.update(fileTask, advance=1)
            new_file_path = os.path.join(inProgressFolder, fileName)
            progress.update(fileTask, advance=1)
            os.rename(old_file_path, new_file_path)
            progress.update(fileTask, advance=1)
            progress.update(task, advance=1)

        if not files:
            progress.update(task, completed=1)
    console.print("All Files Moved!\n")


def CleanBooks():
    files = [f for f in os.listdir(inProgressFolder) if f.endswith(".epub")]
    with Progress(console=console) as progress:
        if files:
            task = progress.add_task("Cleaning EPUB Files: ", total=len(files))
        else:
            task = progress.add_task("Cleaning EPUB Files: ", total=1)

        for fileName in files:
            file = inProgressFolder + fileName
            try:
                book = epubfile.Epub(file)
                fileTask = progress.add_task(
                    f"Cleaning {FitToScreen(fileName)}: ",
                    total=len(book.get_texts()),
                )
                for page in book.get_texts():
                    soup = book.read_file(page)
                    soup = soup.replace(stringToRemove, "")
                    book.write_file(page, soup)
                    progress.update(fileTask, advance=1)

                book.save(file)
                progress.update(task, advance=1)
            except FileNotFoundError as e:
                fileTask = progress.add_task(
                    f"[red]Cleaning {FitToScreen(fileName)}:", total=1
                )
                ErroredFile(inProgressFolder, fileName)
                progress.update(task, advance=1)

        if not files:
            progress.update(task, completed=1)
    console.print("All Files Cleaned!\n")


def FitToScreen(input):
    return textwrap.shorten(
        input, width=shutil.get_terminal_size().columns - 10, placeholder="..."
    )


def GetBookImage(sourceLink="", bookName=""):
    sourceLink = sourceLink.split(".")[0]
    sourceLink = "https://goodreads.com" + sourceLink
    console.print(f"Getting Book Image...")
    response = GetResponse(sourceLink)
    if response.status_code == 200:
        ClearLine()
        console.print(f"\rDownloading Book Image...")
        image_url = (
            BeautifulSoup(response.content, "html.parser")
            .select(".BookCover__image")[0]
            .find("img", class_="ResponsiveImage")["src"]
        )
        default_image_url = image_url
        while True:
            query_parameters = {"downloadformat": "jpg"}
            image_file = bookName + ".jpg"
            image_response = GetResponse(image_url, query_parameters)
            if image_response.status_code == 200:
                with open(inProgressFolder + image_file, "wb") as f:
                    f.write(image_response.content)
                    ClearLine()
                with Image.open(inProgressFolder + image_file) as image:
                    new_image = image.convert("RGB")
                    new_image = new_image.resize([1600, 2560])
                    new_image.save(inProgressFolder + image_file)
                viewer.ShowCover(inProgressFolder + image_file)
                image_confirm = Confirm.ask(
                    f"Use This Book Cover?", default=True
                )
                ClearLine()
                if image_confirm:
                    console.print("\rGetting Book Image: Done!")
                    return image_file
                else:
                    console.print(
                        "Please Enter Cover URL (Leave Blank for Default)"
                    )
                    image_url = input("")
                    screen_width = shutil.get_terminal_size().columns
                    ClearLine((len(image_url) // screen_width) + 1)
                    if image_url == "":
                        image_url = default_image_url


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
        except:
            time.sleep()


def SearchBook(fileName):
    manual_search = False
    while True:
        query = "+".join(
            fileName.replace("_OceanofPDF.com_", " ")
            .replace("-", " ")
            .replace("_", " ")
            .replace("(", "")
            .replace(")", "")
            .replace(".epub", "")
            .split()
        )
        if manual_search:
            console.print(
                f"\rManual Search For [white]{FitToScreen(fileName)}[/white] - (Leave blank to skip)"
            )
            query = "+".join(
                Prompt.ask(
                    f"Please Enter Search Term (Leave Blank To Skip)",
                    default="",
                )
                .replace(" ", "+")
                .split()
            )
            ClearLine()
            if query == "":
                return False
            ClearLine()
        query_normal = FitToScreen(query.replace("+", " "))
        console.print(f"Searching {FitToScreen(query_normal)}...")
        url = f"https://www.goodreads.com/search?q={query}"
        response = GetResponse(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            results = soup.select("tr")
            ClearLine()
            console.print(
                f"\rSearching {FitToScreen(query_normal)}: {len(results)}"
            )
            if results:
                console.print(f"Results for [white]{query_normal}[/white]:")
                console.print(f"- - Enter Different Search Term")
                console.print(f"+ - Skip Book")
                for i in range(len(results)):
                    book_title = textwrap.shorten(
                        results[i].select(".bookTitle")[0].text.strip(),
                        width=shutil.get_terminal_size().columns - 10,
                        placeholder="...",
                    )
                    console.print(f"{i} - {book_title}")
                selection = Prompt.ask(
                    "Please Select Book - Leave Blank For Default:)",
                    default="0",
                )
                ClearLine(len(results) + 4)
                if selection == "+":
                    return False
                if selection == "-":
                    ClearLine()
                    manual_search = True
                    continue
                selection = int(selection)
                book_title = (
                    results[selection].select(".bookTitle")[0].text.strip()
                )
                book_author = (
                    results[selection].select(".authorName")[0].text.strip()
                )
                book_image = str(
                    results[selection].select(".bookTitle")[0]["href"]
                )
                return book_title, book_author, book_image
            else:
                ClearLine()
                manual_search = True


def ConfirmMetadata():
    files = [f for f in os.listdir(inProgressFolder) if f.endswith(".epub")]
    console.print(f"Correcting Book Metadata For {len(files)} Books:")
    for fileName in files:
        file = inProgressFolder + fileName
        book_data = SearchBook(fileName)
        if book_data:
            try:
                meta = ebookmeta.get_metadata(file)
                meta.title = book_data[0]
                meta.set_author_list_from_string(book_data[1])
                ebookmeta.set_metadata(file, meta)
                book = epubfile.Epub(file)
                book_image = GetBookImage(book_data[2], fileName)
                cover_id = book.get_cover_image()
                with open(inProgressFolder + book_image, "rb") as img:
                    img_data = img.read()
                    book.write_file(cover_id, img_data)
                book.save(file)
                console.print(f"{book_data[0]} - Updated!")
            except KeyError as e:
                console.print(
                    f"\r[red]ERROR - {FitToScreen(fileName)} - Skpping!"
                )
                ErroredFile(inProgressFolder, fileName)
        else:
            ClearLine()
            console.print(f"\r[red]NOTE - {FitToScreen(fileName)} - Skipping")
            old_file_path = inProgressFolder + fileName
            new_file_path = erroredFolder + fileName
            os.rename(old_file_path, new_file_path)

    console.print("All Book's Metadata Updated!\n")


def CleanFolders():
    files = [f for f in os.listdir(inProgressFolder) if f.endswith(".jpg")]
    with Progress(console=console) as progress:
        if files:
            task = progress.add_task("Deleting JPG Files: ", total=len(files))
        else:
            task = progress.add_task("Deleting JPG Files: ", total=1)

        for fileName in files:
            file = inProgressFolder + fileName
            os.remove(file)
            progress.update(task, advance=1)

        if not files:
            progress.update(task, completed=1)
    console.print("All JPG Files Deleted!\n")


def MoveToDone():
    files = [f for f in os.listdir(inProgressFolder) if f.endswith(".epub")]
    with Progress(console=console) as progress:
        if files:
            task = progress.add_task(
                "Collecting EPUB Files:", total=len(files)
            )
        else:
            task = progress.add_task("Collecting EPUB Files:", total=1)

        for fileName in files:
            fileTask = progress.add_task(
                f"Moving {FitToScreen(fileName)}", total=3
            )
            old_file_path = os.path.join(inProgressFolder, fileName)
            progress.update(fileTask, advance=1)
            new_file_path = os.path.join(doneFolder, fileName)
            progress.update(fileTask, advance=1)
            os.rename(old_file_path, new_file_path)
            progress.update(fileTask, advance=1)
            progress.update(task, advance=1)

        if not files:
            progress.update(task, completed=1)
    console.print("All Files Moved!\n")


def End():
    console.print("All Files Have Been Cleaned!")
    input("Please press any key to close this window...")


def ErroredFile(location, fileName):
    os.rename(location + fileName, erroredFolder + fileName)


viewer = ImageViewer()
Start()
CheckFolders()
MoveToInProgress()
CleanBooks()
ConfirmMetadata()
CleanFolders()
RenameFiles()
MoveToDone()
End()
