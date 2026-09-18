@echo off
setlocal
cd /d "%~dp0"
python "%~dp0netbench.py" %*
if %ERRORLEVEL% NEQ 0 (
    pause
)
