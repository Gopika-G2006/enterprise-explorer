@echo off
echo Starting Enterprise Intelligence Explorer Backend...
cd /d "%~dp0backend"
py -3 -m uvicorn main:app --reload --port 8000
