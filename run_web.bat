@echo off
title AniBatch Web Dashboard
echo ========================================================
echo   AniBatch Local Web Dashboard
echo ========================================================
echo.
echo Starting AniBatch Web Dashboard...
echo.
uv run anibatch web
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo AniBatch encountered an error (exit code %ERRORLEVEL%).
    pause
)
