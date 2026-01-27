@echo off
setlocal

set "ROOT=%~dp0"
set "PY=%ROOT%..\.venv-win\Scripts\python.exe"
set "SCRIPT=%ROOT%GoGoGyroDesktopAligned60s.py"

if not exist "%PY%" (
  echo [GoGoGyro] Missing venv: "%PY%"
  echo Create it with: py -3 -m venv .venv-win
  echo Then install pygame: .venv-win\Scripts\python.exe -m pip install pygame
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
