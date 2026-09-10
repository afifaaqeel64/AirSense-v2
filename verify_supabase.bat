@echo off
cd /d "%~dp0"
title AirSense - Verify Live Supabase PostgreSQL Connection
echo ==============================================================================
echo   AirSense Pakistan - Live Supabase PostgreSQL Verification
echo   Working Directory: %cd%
echo ==============================================================================
echo.
py scripts/test_live_ingestion_supabase.py
echo.
echo ==============================================================================
echo Verification finished!
echo ==============================================================================
pause
