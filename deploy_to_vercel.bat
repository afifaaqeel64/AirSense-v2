@echo off
cd /d "%~dp0"
title AirSense - Deploy 24/7 Standalone Cloud Dashboard to Vercel
echo ==============================================================================
echo   AirSense Pakistan - 24/7 Standalone Cloud Dashboard Deployment
echo   Target: Vercel Cloud (Zero Laptop Dependency, Global CDN)
echo   Project Name: airsense-team
echo   Working Directory: %cd%
echo ==============================================================================
echo.
echo [Step 1] Verifying Vercel Authentication...
cmd /c npx vercel whoami
echo.
echo [Step 2] Deploying Standalone Dashboard to airsense-team...
echo - Public directory: public/
echo - Direct Cloud MQTT WebSockets: wss://broker.hivemq.com:8884/mqtt
echo.
cmd /c npx vercel public --prod --yes --name airsense-team
echo.
echo ==============================================================================
echo Deployment completed! Open your live URL on any mobile phone or computer!
echo ==============================================================================
pause
