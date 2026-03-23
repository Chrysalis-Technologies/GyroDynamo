@echo off
setlocal
set "REPO_DIR=%~dp0"

if exist "%REPO_DIR%.venv-win\Scripts\python.exe" (
  "%REPO_DIR%.venv-win\Scripts\python.exe" -m audacity_bridge.cli %*
  exit /b %ERRORLEVEL%
)

py -3 -m audacity_bridge.cli %*
exit /b %ERRORLEVEL%
