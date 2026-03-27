@echo off
title SeeSky Backend (Flask :5000)
cd /d "%~dp0backend"
call "%~dp0venv\Scripts\activate.bat"
python app.py
pause
