@echo off
chcp 65001 >nul
title HH Auto Reply Bot — CLI Dashboard

set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

if not exist "%PY_EXE%" (
    set "PY_EXE=python"
)

if "%1"=="--direct" (
    "%PY_EXE%" bot.py
) else (
    "%PY_EXE%" menu.py
)

if errorlevel 1 (
    echo.
    pause
)
