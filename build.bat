@echo off
REM Genera dist\ToledoDiagnosis.exe (un solo archivo, sin consola)
cd /d "%~dp0"
python -m pip install -q -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name ToledoDiagnosis ^
  --icon "%~dp0icono.ico" ^
  --add-data "%~dp0icono.ico;." ^
  --hidden-import simulador ^
  --hidden-import serial.tools.list_ports ^
  --collect-submodules anthropic ^
  --collect-submodules openai ^
  --distpath dist --workpath build --specpath build ^
  gui.py
echo.
echo Ejecutable: %~dp0dist\ToledoDiagnosis.exe
