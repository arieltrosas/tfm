#!/bin/bash

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/ai-agent"
FRONTEND_DIR="$ROOT_DIR/user-client"
DEBUG_OUT="$ROOT_DIR/build/macos/debug"
RELEASE_OUT="$ROOT_DIR/build/macos/release"

echo "============================================"
echo " 1. Cleaning & Preparing Build Directories  "
echo "============================================"

rm -rf "$ROOT_DIR/build/macos"
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
godot --headless --export-debug "macOS" "$DEBUG_OUT/frontend.app"

echo "-> Exporting Release Game..."
godot --headless --export-release "macOS" "$RELEASE_OUT/frontend.app"

echo "============================================"
echo " 4. Assembling Components                    "
echo "============================================"

# Places the backend executable right alongside the .app bundle
cp "$BACKEND_BINARY" "$DEBUG_OUT/backend"
cp "$BACKEND_BINARY" "$RELEASE_OUT/backend"

echo "============================================"
echo " Build Successful!                          "
echo "============================================"
echo "Debug Located at '$DEBUG_OUT'"
echo "Release Located at '$RELEASE_OUT'"
