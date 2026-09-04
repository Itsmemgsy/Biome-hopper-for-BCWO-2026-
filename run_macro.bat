@echo off
title Biome Hopper 3000
cd /d "%~dp0"
del run_flag.txt 2>nul
pythonw settings_gui.py
if not exist run_flag.txt goto :end
del run_flag.txt
echo ============================================
echo   BIOME HOPPER 3000 - macro running
echo   F9 to stop. Watch this window for status.
echo ============================================
python biome_hopper.py
echo.
echo Macro stopped. Press any key to close.
pause >nul
:end
