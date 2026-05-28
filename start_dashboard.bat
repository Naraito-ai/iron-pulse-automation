@echo off
title AI Instagram Automation — Dashboard
color 0B
echo.
echo  ============================================================
echo   AI INSTAGRAM AUTOMATION SYSTEM — DASHBOARD
echo  ============================================================
echo.
echo  Starting the Next.js Dashboard locally...
echo  (It will connect to your live Railway cloud API)
echo.

cd /d "D:\ai-instagram-automation\dashboard"

:: Check if node modules are installed
if not exist "node_modules\" (
    echo [INFO] Installing dashboard dependencies first...
    call npm install
)

:: Start the Next.js dashboard
start "Dashboard Next.js" cmd /c "npm run dev"

:: Wait for it to boot
timeout /t 5 /nobreak >nul

:: Open browser
start http://localhost:3000

echo.
echo  [OK] Dashboard launched successfully!
echo  [OK] URL: http://localhost:3000
echo.
pause
