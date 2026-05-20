@echo off
REM Double-click ONLY if welcome.html reports the supervisor is unreachable.
REM
REM Normal flow: welcome.html auto-wakes bridges via the supervisor on 8764.
REM This is the fallback for when even the supervisor isn't running.
REM
REM Stops then restarts each scheduled task. Idempotent.

setlocal

set ANY_FAIL=0

for %%N in (supervisor command-center website-build website-rebuild) do (
  schtasks /End /TN "SearchAtlasAMM-%%N" >nul 2>&1
  schtasks /Run /TN "SearchAtlasAMM-%%N" >nul 2>&1
  if errorlevel 1 (
    echo   [X]  %%N failed to restart
    set ANY_FAIL=1
  ) else (
    echo   [OK] %%N restarted
  )
)

echo.
if "%ANY_FAIL%"=="0" (
  echo All services restarted. Refresh welcome.html, then click any wizard card.
) else (
  echo Some services failed to restart. Re-run quickstart-windows.ps1 to repair scheduled tasks.
)
echo.
pause
endlocal
