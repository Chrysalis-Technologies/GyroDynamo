@echo off
setlocal

set "ROOT=%~dp0.."
set "PY=%ROOT%\.venv-win-build\Scripts\python.exe"
set "ENTRY=%ROOT%\Dynam0\GyroDynamoVisPy.py"
set "CONFIG=%ROOT%\Dynam0\gyro_desktop_config.json"

if not exist "%PY%" (
  echo [GyroDynamo] Creating build venv at "%ROOT%\.venv-win-build"
  py -3 -m venv "%ROOT%\.venv-win-build"
  if errorlevel 1 exit /b 1
)

"%PY%" -m pip install --upgrade pip
if errorlevel 1 exit /b 1

"%PY%" -m pip install -r "%ROOT%\requirements-desktop.txt" -r "%ROOT%\requirements-build.txt"
if errorlevel 1 exit /b 1

if not exist "%ENTRY%" (
  echo [GyroDynamo] Missing entrypoint: "%ENTRY%"
  exit /b 1
)

"%PY%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name GyroDynamoDesktop ^
  --distpath "%ROOT%\dist" ^
  --workpath "%ROOT%\build\pyinstaller" ^
  --specpath "%ROOT%\build\pyinstaller" ^
  --add-data "%CONFIG%;Dynam0" ^
  --exclude-module pygame ^
  --exclude-module PIL ^
  "%ENTRY%"
if errorlevel 1 exit /b 1

echo [GyroDynamo] Build complete: "%ROOT%\dist\GyroDynamoDesktop\GyroDynamoDesktop.exe"
