@echo off
cd /d "%~dp0"
echo ===================================================
echo Pushing AniBatch to GitHub: https://github.com/sfaiq19/Ani_batch
echo ===================================================
echo.
git push -u origin main
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Git push failed. If prompted, please sign in through the browser.
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo [SUCCESS] Repository pushed to GitHub!
pause
