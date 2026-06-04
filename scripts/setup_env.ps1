# PowerShell script to create venv and install requirements
param()
$cwd = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $cwd\..  # project root
if (-not (Test-Path -Path .venv)) {
    python -m venv .venv
}
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
Write-Host "Virtual environment ready in .venv and requirements installed."