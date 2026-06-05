#!/bin/bash

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/ai-agent"
FRONTEND_DIR="$ROOT_DIR/user-client"
DEBUG_OUT="$ROOT_DIR/build/linux/debug"
RELEASE_OUT="$ROOT_DIR/build/linux/release"

echo "============================================"
echo " 1. Cleaning & Preparing Build Directories  "
echo "============================================"

rm -rf "$ROOT_DIR/build/linux"
mkdir -p "$DEBUG_OUT"
mkdir -p "$RELEASE_OUT"

echo "============================================"
echo " 2. Compiling Python Backend (PyInstaller)   "
echo "============================================"
cd "$BACKEND_DIR"

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment (.venv) not found in $BACKEND_DIR"
    exit 1
fi

pyinstaller --onefile main.py

BACKEND_BINARY="$BACKEND_DIR/dist/main"
deactivate

echo "============================================"
echo " 3. Exporting Godot Frontend                "
echo "============================================"
cd "$FRONTEND_DIR"

echo "-> Exporting Debug Game..."
godot --headless --export-debug "Linux" "$DEBUG_OUT/frontend.x86_64"

echo "-> Exporting Release Game..."
godot --headless --export-release "Linux" "$RELEASE_OUT/frontend.x86_64"

echo "============================================"
echo " 4. Assembling Components                   "
echo "============================================"

cp "$BACKEND_BINARY" "$DEBUG_OUT/backend"
cp "$BACKEND_BINARY" "$RELEASE_OUT/backend"

echo "============================================"
echo " Build Successful!                          "
echo "============================================"
echo "Debug Localted at '$DEBUG_OUT'"
echo "Release Localted at '$RELEASE_OUT'"

