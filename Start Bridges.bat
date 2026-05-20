@echo off
REM Double-click to restart the Mission Control bridges.
REM
REM This stops the existing scheduled tasks and restarts them.

setlocal

for %%N in (command-center website-build website-rebuild) do (
  schtasks /End /TN "SearchAtlasAMM-%%N" >nul 2>&1
  schtasks /Run /TN "SearchAtlasAMM-%%N" >nul 2>&1
  if errorlevel 1 (
    echo   [X]  %%N bridge failed to restart
  ) else (
    echo   [OK] %%N bridge restarted
  )
)

echo.
echo Bridges restarted. Open welcome.html and click any wizard card.
echo.
pause
endlocal
