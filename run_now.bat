@echo off
title Run Pipeline Now
echo.
echo  Triggering AI Instagram pipeline manually...
echo.
cd /d D:\ai-instagram-automation
python backend\main.py --run-now --no-scheduler
echo.
echo  Pipeline complete! Check the dashboard at http://localhost:3000
pause
