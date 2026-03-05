@echo off
echo Starting Enterprise Intelligence Explorer Frontend...
cd /d "%~dp0frontend"
py -3 -m http.server 3000
