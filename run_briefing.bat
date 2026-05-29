@echo off
cd /d C:\Users\lenovo\Desktop\daily-briefing
call venv\Scripts\activate.bat
python daily_briefing.py >> logs\scheduler.log 2>&1
