@echo off
title Network Benchmark Host (iPerf3 + HTTP Sink)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_servers.ps1"
pause
