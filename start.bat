@echo off
REM One-command launcher for MailPilot (Windows).
REM   start.bat            -> installs deps into a local venv, then starts the app
REM   set PORT=8080 & start.bat  -> run on a different port
REM
REM Open http://localhost:5001 (or your chosen PORT) in a browser once it prints
REM "Running on ...".
setlocal
cd /d "%~dp0"

REM pick a python launcher
where py >nul 2>nul && (set PY=py) || (set PY=python)

if not exist ".venv" (
  echo ==^> Creating virtual environment (.venv)...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo ERROR: Python 3.10+ is required but was not found. Install it from python.org.
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"

echo ==^> Installing dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

if "%PORT%"=="" set PORT=5001
echo.
echo ======================================================================
echo   MailPilot is starting.
echo   Open your browser at:  http://localhost:%PORT%
echo   Press Ctrl+C to stop.
echo ======================================================================
echo.
python run_saas.py
pause
