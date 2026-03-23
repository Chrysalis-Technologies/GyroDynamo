@echo off
setlocal

set "ROOT=%~dp0"
set "PY=%ROOT%..\.venv-win\Scripts\python.exe"
set "SCRIPT=%ROOT%GyroDynamoVisPy.py"

if not exist "%PY%" (
  echo [GyroDynamoVisPy] Missing venv: "%PY%"
  echo Create it with: py -3 -m venv .venv-win
  echo Then install desktop deps: .venv-win\Scripts\python.exe -m pip install -r requirements-desktop.txt
  pause
  exit /b 1
)

"%PY%" -c "import sys" >nul 2>&1
if errorlevel 1 (
  echo [GyroDynamoVisPy] Python venv is not runnable: "%PY%"
  echo Delete and recreate it with: py -3 -m venv .venv-win
  pause
  exit /b 1
)

"%PY%" -c "import numpy, vispy" >nul 2>&1
if errorlevel 1 (
  echo [GyroDynamoVisPy] Missing required packages in venv.
  echo Install them with: .venv-win\Scripts\python.exe -m pip install -r requirements-desktop.txt
  pause
  exit /b 1
)

if not exist "%SCRIPT%" (
  echo [GyroDynamoVisPy] Missing script: "%SCRIPT%"
  pause
  exit /b 1
)

"%PY%" "%SCRIPT%" %*
if errorlevel 1 pause
