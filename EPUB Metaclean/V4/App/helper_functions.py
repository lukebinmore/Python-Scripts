import sys
import os
from PIL import Image
from io import BytesIO


def resourcePath(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def checkBookExists(books, target_key, target_val):
    return any(getattr(book, target_key, False) == target_val for book in books)


def resizeCoverImage(img_data):
    image = Image.open(BytesIO(img_data))
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    image = image.resize((1600, 2560), Image.Resampling.LANCZOS)

    output = BytesIO()
    image.save(output, format="JPEG", quality=95)

    return output.getvalue()
