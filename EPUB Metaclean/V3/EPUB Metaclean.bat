@echo off
pip install Pillow epubfile requests ebookmeta beautifulsoup4 selenium undetected-chromedriver 
set "pythonFile=%~dp0EPUB Metaclean.py"
python "%pythonFile%"