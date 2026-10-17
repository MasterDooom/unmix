@echo off
setlocal
cd /d "%~dp0"
echo Starting Unmix locally. The first install may take several minutes.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0web\start-local.ps1"
if errorlevel 1 (
  echo.
  echo Unmix did not start successfully. Read the error above, then press any key.
  pause >nul
)
endlocal
