#!/bin/bash

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/ai-agent"
FRONTEND_DIR="$ROOT_DIR/user-client"
DEBUG_OUT="$ROOT_DIR/build/windows/debug"
RELEASE_OUT="$ROOT_DIR/build/windows/release"

echo "============================================"
echo " 1. Cleaning & Preparing Build Directories  "
echo "============================================"

rm -rf "$ROOT_DIR/build/windows"
mkdir -p "$DEBUG_OUT"
mkdir -p "$RELEASE_OUT"

echo "============================================"
echo " 2. Compiling Python Backend (PyInstaller)   "
echo "============================================"
cd "$BACKEND_DIR"

if [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
else
    echo "Error: Virtual environment (.venv) not found in $BACKEND_DIR"
    exit 1
fi

pyinstaller --onefile main.py

BACKEND_BINARY="$BACKEND_DIR/dist/main.exe"
deactivate

echo "============================================"
echo " 3. Exporting Godot Frontend                "
echo "============================================"
cd "$FRONTEND_DIR"

echo "-> Exporting Debug Game..."
godot --headless --export-debug "Windows" "$DEBUG_OUT/frontend.exe"

echo "-> Exporting Release Game..."
godot --headless --export-release "Windows" "$RELEASE_OUT/frontend.exe"

echo "============================================"
echo " 4. Assembling Components                    "
echo "============================================"

cp "$BACKEND_BINARY" "$DEBUG_OUT/backend.exe"
cp "$BACKEND_BINARY" "$RELEASE_OUT/backend.exe"

echo "============================================"
echo " Build Successful!                           "
echo "============================================"
echo "Debug Located at '$DEBUG_OUT'"
echo "Release Located at '$RELEASE_OUT'"
