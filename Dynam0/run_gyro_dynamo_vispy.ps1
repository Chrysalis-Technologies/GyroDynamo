$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $root
$python = Join-Path $projectRoot '.venv-win\Scripts\python.exe'
$script = Join-Path $root 'GyroDynamoVisPy.py'

if (-not (Test-Path $python)) {
    Write-Host "[GyroDynamoVisPy] Missing venv: `"$python`""
    Write-Host 'Create it with: py -3 -m venv .venv-win'
    Write-Host 'Then install desktop deps: .venv-win\Scripts\python.exe -m pip install -r requirements-desktop.txt'
    exit 1
}

$global:LASTEXITCODE = 0
& $python -c "import sys" *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[GyroDynamoVisPy] Python venv is not runnable: `"$python`""
    Write-Host 'Delete and recreate it with: py -3 -m venv .venv-win'
    exit 1
}

$global:LASTEXITCODE = 0
& $python -c "import numpy, vispy, glfw" *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host '[GyroDynamoDesktop] Missing required packages in venv.'
    Write-Host 'Install them with: .venv-win\Scripts\python.exe -m pip install -r requirements-desktop.txt'
    exit 1
}

if (-not (Test-Path $script)) {
    Write-Host "[GyroDynamoVisPy] Missing script: `"$script`""
    exit 1
}

Start-Process -FilePath $python -ArgumentList (@($script) + $args) -WorkingDirectory $root
