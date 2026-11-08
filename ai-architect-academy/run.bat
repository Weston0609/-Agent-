@echo off
REM 启动本地 Web 学习面板（浏览器自动打开 http://127.0.0.1:8000）
cd /d "%~dp0"
start "" http://127.0.0.1:8000
python -m src.web
pause
