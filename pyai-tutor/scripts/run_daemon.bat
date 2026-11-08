@echo off
REM pyai-tutor 常驻守护（Windows）—— 15s tick 实时感知时间，到点提醒上课。
REM 用法：双击运行；或把本文件的快捷方式放进
REM   shell:startup   （开机自启）
REM 或注册到「任务计划程序」→ 触发器「登录时」→ 操作「启动程序」指向本文件。
setlocal
set PYTHONUTF8=1
cd /d "%~dp0.."
where pyai >nul 2>nul
if %errorlevel%==0 (
  pyai daemon
) else (
  python -m pyai.daemon
)
pause
