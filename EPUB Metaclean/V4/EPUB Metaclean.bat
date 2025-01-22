@echo off
pip install PyQt5 epubfile ebookmeta beautifulsoup4 
set "pythonFile=%~dp0EPUB Metaclean.py"
python "%pythonFile%"