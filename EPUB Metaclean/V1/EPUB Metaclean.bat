@echo off
pip install rich epubfile ebookmeta requests bs4 textwrap shutil tkinter
cls
set "pythonFile=%~dp0EPUB Metaclean.py"
python "%pythonFile%"