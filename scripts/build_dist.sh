#!/bin/bash
set -e

# Ensure we are in the project root
cd "$(dirname "$0")/.."

echo "Building Conestoga for macOS..."

# Install dependencies if needed (assuming uv is used)
uv sync --all-extras

# Create downloads directory
mkdir -p web/downloads

# Build with PyInstaller
# --onefile: Create a single executable
# --name: Name of the executable
# --clean: Clean PyInstaller cache
# --windowed: No console window (GUI app)
uv run pyinstaller --noconfirm --onefile --windowed --name "Conestoga" \
    --hidden-import="pygame" \
    --hidden-import="google.genai" \
    --hidden-import="dotenv" \
    src/conestoga/main.py

echo "Build complete. Packaging..."

# Zip the macOS app
cd dist
zip -r ../web/downloads/Conestoga-macOS.zip Conestoga.app
cd ..

# Create a placeholder for Windows (since we can't cross-compile easily with PyInstaller)
echo "Windows build requires running this script on Windows." > web/downloads/README_WINDOWS.txt
zip web/downloads/Conestoga-Windows.zip web/downloads/README_WINDOWS.txt

echo "Binaries prepared in web/downloads/"
ls -lh web/downloads/
