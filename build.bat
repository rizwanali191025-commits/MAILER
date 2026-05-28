@echo off
REM ============================================================
REM  Bulk Gmail Mailer — Windows build script
REM  Run this once from a Command Prompt in the project folder:
REM      build.bat
REM ============================================================

echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Download from https://python.org
    pause & exit /b 1
)

echo [2/4] Installing dependencies...
pip install -r requirements.txt --quiet
pip install pyinstaller pystray --quiet

echo [3/4] Generating icon...
python assets\generate_icon.py

echo [4/4] Building executable with PyInstaller...
pyinstaller mailer.spec --clean --noconfirm

if exist "dist\BulkMailer\BulkMailer.exe" (
    echo.
    echo =====================================================
    echo  BUILD COMPLETE
    echo  Executable:  dist\BulkMailer\BulkMailer.exe
    echo.
    echo  To create a Windows installer:
    echo    1. Install Inno Setup from https://jrsoftware.org
    echo    2. Open installer\setup.iss in Inno Setup
    echo    3. Press Ctrl+F9 to compile the installer
    echo  The installer will appear as: dist\BulkMailer_Setup.exe
    echo =====================================================
) else (
    echo ERROR: Build failed. Check the output above for errors.
)

pause
