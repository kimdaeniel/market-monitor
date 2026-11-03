@echo off
cd /d "%~dp0"
if not exist data mkdir data
".venv\Scripts\python.exe" run.py >> data\run.log 2>&1
