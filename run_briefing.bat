@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
call venv\Scripts\activate.bat
python daily_briefing.py >> logs\scheduler.log 2>&1
