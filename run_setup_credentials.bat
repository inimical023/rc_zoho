@echo off
call .venv\Scripts\activate.bat
python setup_credentials.py %*
