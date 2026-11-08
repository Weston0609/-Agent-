@echo off
chcp 936 >nul
cd /d "%~dp0"
title pyai-tutor 学习系统

set "PYTHONPATH=%CD%\src"
set "PY="

if exist ".venv\Scripts\python.exe" set "PY=%CD%\.venv\Scripts\python.exe"

if not defined PY (
    where python >nul 2>nul
    if not errorlevel 1 set "PY=python"
)

if not defined PY (
    echo.
    echo   没有找到 Python，无法启动。
    echo.
    echo   请先安装 Python 3.10 或更高版本：https://www.python.org/downloads/
    echo   安装时务必勾选 "Add Python to PATH"。
    echo.
    pause
    exit /b 1
)

echo.
echo   正在启动 pyai-tutor 学习系统...
echo.
echo   界面地址：http://127.0.0.1:8000
echo   浏览器会在几秒后自动打开。
echo.
echo   * 学习数据存在本机，全程离线，不消耗任何 token。
echo   * 关闭标题为「学习系统」的那个窗口，即可退出。
echo.

start "pyai-tutor 学习系统" "%PY%" -X utf8 -m pyai.ui.cli web --port 8000

timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:8000/

exit /b 0