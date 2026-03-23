@echo off
setlocal

set "ROOT=%~dp0"
set "PY=%ROOT%..\.venv-win\Scripts\python.exe"
set "SCRIPT=%ROOT%GoGoGyroDesktopAligned30s.py"

if not exist "%PY%" (
  echo [GoGoGyro] Missing venv: "%PY%"
  echo Create it with: py -3 -m venv .venv-win
  echo Then install pygame: .venv-win\Scripts\python.exe -m pip install pygame
  pause
  exit /b 1
)

rem Sanity-check venv runtime (helps detect a broken base Python install).
"%PY%" -c "import sys" >nul 2>&1
if errorlevel 1 (
  echo [GoGoGyro] Python venv is not runnable: "%PY%"
  echo Delete and recreate it with: py -3 -m venv .venv-win
  pause
  exit /b 1
)

rem Ensure pygame is installed before launching the visualizer.
"%PY%" -c "import pygame" >nul 2>&1
if errorlevel 1 (
  echo [GoGoGyro] pygame is not installed in this venv.
  echo Install it with: .venv-win\Scripts\python.exe -m pip install pygame
  pause
  exit /b 1
)

if not exist "%SCRIPT%" (
  echo [GoGoGyro] Missing script: "%SCRIPT%"
  pause
  exit /b 1
)

"%PY%" "%SCRIPT%"
if errorlevel 1 pause
