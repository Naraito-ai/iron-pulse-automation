@echo off
title AI Instagram Automation System — Launcher
color 0A
echo.
echo  ============================================================
echo   AI INSTAGRAM AUTOMATION SYSTEM — STARTUP
echo  ============================================================
echo.
echo  Starting services...
echo.

:: Start Python API + Scheduler (background)
start "Backend API + Scheduler" cmd /k "cd /d D:\ai-instagram-automation && python backend\api_server.py"

:: Wait for API to come up
timeout /t 4 /nobreak >nul

:: Start main scheduler (background)
start "Pipeline Scheduler" cmd /k "cd /d D:\ai-instagram-automation && python backend\main.py"

:: Wait a moment
timeout /t 3 /nobreak >nul

:: Start Next.js dashboard
start "Dashboard" cmd /k "cd /d D:\ai-instagram-automation\dashboard && npm run dev"

:: Wait for dashboard
timeout /t 5 /nobreak >nul

:: Open browser
start http://localhost:3000

echo.
echo  [OK] All services started!
echo  [OK] Dashboard: http://localhost:3000
echo  [OK] Backend API: http://localhost:8000
echo  [OK] API Docs: http://localhost:8000/docs
echo  [OK] Images: http://localhost:8888
echo.
echo  To trigger a manual pipeline run, visit:
echo  http://localhost:8000/docs#/default/trigger_pipeline_api_trigger_post
echo.
pause
