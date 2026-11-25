@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (
    python -m venv .venv || goto :fail
)
call .venv\Scripts\activate || goto :fail
python -m pip install --upgrade pip || goto :fail
pip install -r requirements.txt pyinstaller || goto :fail
python build_exe.py || goto :fail
echo.
echo Done. Your program is at: dist\EngineeringEconomy.exe
pause
exit /b 0
:fail
echo.
echo Build failed. Make sure Python 3.10+ is installed and on PATH.
pause
exit /b 1
