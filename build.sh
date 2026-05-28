#!/usr/bin/env bash
# ============================================================
#  Bulk Gmail Mailer — macOS / Linux build script
#  Run from the project folder:  bash build.sh
# ============================================================
set -e

echo "[1/4] Checking Python..."
python3 --version

echo "[2/4] Installing dependencies..."
pip3 install -r requirements.txt --quiet
pip3 install pyinstaller pystray --quiet

echo "[3/4] Generating icon..."
python3 assets/generate_icon.py

echo "[4/4] Building with PyInstaller..."
pyinstaller mailer.spec --clean --noconfirm

if [ -f "dist/BulkMailer/BulkMailer" ]; then
    echo ""
    echo "====================================================="
    echo " BUILD COMPLETE"
    echo " Run with:  dist/BulkMailer/BulkMailer"
    echo " Or double-click dist/BulkMailer/BulkMailer"
    echo "====================================================="
else
    echo "ERROR: Build failed. Check the output above."
    exit 1
fi
