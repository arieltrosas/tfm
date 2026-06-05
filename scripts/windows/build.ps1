$ErrorActionPreference = "Stop"

# Resolves the root directory (2 levels up from where this script sits)
$ROOT_DIR = (Get-Item "$PSScriptRoot\..\..").FullName
$BACKEND_DIR = "$ROOT_DIR\ai-agent"
$FRONTEND_DIR = "$ROOT_DIR\user-client"
$DEBUG_OUT = "$ROOT_DIR\build\windows\debug"
$RELEASE_OUT = "$ROOT_DIR\build\windows\release"

Write-Host "============================================"
Write-Host " 1. Cleaning & Preparing Build Directories  "
Write-Host "============================================"

if (Test-Path "$ROOT_DIR\build\windows") { 
    Remove-Item -Recurse -Force "$ROOT_DIR\build\windows" 
}
New-Item -ItemType Directory -Force $DEBUG_OUT | Out-Null
New-Item -ItemType Directory -Force $RELEASE_OUT | Out-Null

Write-Host "============================================"
Write-Host " 2. Compiling Python Backend (PyInstaller)   "
Write-Host "============================================"
Set-Location $BACKEND_DIR

if (Test-Path ".venv\Scripts\Activate.ps1") {
    & ".venv\Scripts\Activate.ps1"
} else {
    Write-Error "Error: Virtual environment (.venv) not found in $BACKEND_DIR"
    Exit 1
}

pyinstaller --onefile main.py

$BACKEND_BINARY = "$BACKEND_DIR\dist\main.exe"
deactivate

Write-Host "============================================"
Write-Host " 3. Exporting Godot Frontend                "
Write-Host "============================================"
Set-Location $FRONTEND_DIR

Write-Host "-> Exporting Debug Game..."
godot --headless --export-debug "Windows" "$DEBUG_OUT\frontend.exe"

Write-Host "-> Exporting Release Game..."
godot --headless --export-release "Windows" "$RELEASE_OUT\frontend.exe"

Write-Host "============================================"
Write-Host " 4. Assembling Components                    "
Write-Host "============================================"

Copy-Item $BACKEND_BINARY "$DEBUG_OUT\backend.exe"
Copy-Item $BACKEND_BINARY "$RELEASE_OUT\backend.exe"

Write-Host "============================================"
Write-Host " Build Successful!                           "
Write-Host "============================================"
Write-Host "Debug Located at '$DEBUG_OUT'"
Write-Host "Release Located at '$RELEASE_OUT'"
