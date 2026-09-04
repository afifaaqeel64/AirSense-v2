@echo off
title AirSense - Deploy Standalone Dashboard to GitHub Pages
echo ==============================================================================
echo   AirSense Pakistan - Deploy to GitHub Pages (24/7 Free Cloud Hosting)
echo ==============================================================================
echo.
echo Checking Git repository status...
git status >nul 2>&1
if %errorlevel% neq 0 (
    echo Initializing Git repository...
    git init
    git branch -M main
)

echo Adding deployment assets in 'public'...
git add public vercel.json
git commit -m "Deploy 24/7 standalone AirSense Cloud Dashboard with direct MQTT WebSockets"

echo.
echo ==============================================================================
echo Ready to push to GitHub!
echo If you haven't linked your GitHub repository yet, run:
echo   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
echo   git push -u origin main
echo.
echo Then go to GitHub Repo -> Settings -> Pages -> Source: Deploy from branch (main / public)
echo ==============================================================================
pause
