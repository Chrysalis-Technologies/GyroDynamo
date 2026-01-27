@echo off
setlocal

set "ROOT=%~dp0"
for %%I in ("%ROOT%..") do set "REPO=%%~fI"

set "PY_CMD="
set "PY_EXE="
set "PY_ARGS="
if defined VIRTUAL_ENV if exist "%VIRTUAL_ENV%\Scripts\python.exe" (
  set "PY_EXE=%VIRTUAL_ENV%\Scripts\python.exe"
) else if exist "%REPO%\.venv-win\Scripts\python.exe" (
  set "PY_EXE=%REPO%\.venv-win\Scripts\python.exe"
) else if exist "%REPO%\.venv\Scripts\python.exe" (
  set "PY_EXE=%REPO%\.venv\Scripts\python.exe"
) else (
  where py >nul 2>&1 && set "PY_EXE=py" && set "PY_ARGS=-3"
)
if not defined PY_EXE set "PY_EXE=python"

"%PY_EXE%" %PY_ARGS% -c "import runpy, sys; sys.argv=[r'%ROOT%recon_orchestrator.py']+sys.argv[1:]; runpy.run_path(sys.argv[0], run_name='__main__')" %*
if errorlevel 1 pause
