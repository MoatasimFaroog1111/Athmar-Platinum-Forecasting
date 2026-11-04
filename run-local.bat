@echo off
setlocal
cd /d "%~dp0"
echo Starting Athmar Precious Metals Intelligence...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-local.ps1"
if errorlevel 1 (
  echo.
  echo Startup failed. Review the message above.
  pause
)
endlocal
