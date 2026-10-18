@echo off
setlocal
cd /d "%~dp0"
if not exist ".build-venv\Scripts\python.exe" py -3 -m venv .build-venv
call .build-venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install "pyinstaller>=6.10,<7"
pyinstaller --noconfirm --clean MCDMVisualStudio.spec
if errorlevel 1 (
  echo Build failed. Review the error above.
  pause
  exit /b 1
)
echo Build complete: dist\MCDMVisualStudio\MCDMVisualStudio.exe
pause
