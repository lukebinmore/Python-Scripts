@echo off
pip install rich epubfile ebookmeta requests
cls
set "pythonFile=%~dp0EPUB Metaclean.py"
python "%pythonFile%"