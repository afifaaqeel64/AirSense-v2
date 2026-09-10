@echo off
echo ========================================================
echo AirSense Pakistan - Git & GitHub Synchronization
echo ========================================================

set GIT_BIN=
if exist "C:\Program Files\Git\cmd\git.exe" set GIT_BIN="C:\Program Files\Git\cmd\git.exe"
if exist "C:\Program Files\Git\bin\git.exe" set GIT_BIN="C:\Program Files\Git\bin\git.exe"
if exist "C:\Program Files (x86)\Git\cmd\git.exe" set GIT_BIN="C:\Program Files (x86)\Git\cmd\git.exe"
if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" set GIT_BIN="%LOCALAPPDATA%\Programs\Git\cmd\git.exe"
if exist "%LOCALAPPDATA%\Programs\Git\bin\git.exe" set GIT_BIN="%LOCALAPPDATA%\Programs\Git\bin\git.exe"
if exist "%ProgramFiles%\Git\cmd\git.exe" set GIT_BIN="%ProgramFiles%\Git\cmd\git.exe"

set GH_BIN=
if exist "C:\Program Files\GitHub CLI\gh.exe" set GH_BIN="C:\Program Files\GitHub CLI\gh.exe"
if exist "%LOCALAPPDATA%\Programs\GitHub CLI\gh.exe" set GH_BIN="%LOCALAPPDATA%\Programs\GitHub CLI\gh.exe"
if exist "%ProgramFiles%\GitHub CLI\gh.exe" set GH_BIN="%ProgramFiles%\GitHub CLI\gh.exe"

echo Git binary: %GIT_BIN%
echo GitHub CLI: %GH_BIN%

if not defined GIT_BIN (
    echo [WARN] git.exe not found in standard system directories. Searching via where command...
    where git > nul 2>&1
    if %errorlevel% equ 0 (
        set GIT_BIN=git
        echo Found git in PATH!
    )
)

if defined GIT_BIN (
    echo.
    echo Initializing and syncing Git repository...
    if not exist ".git" (
        %GIT_BIN% init
        %GIT_BIN% branch -M main
    )
    %GIT_BIN% config user.name "AirSense Team"
    %GIT_BIN% config user.email "dev@airsense.pk"
    %GIT_BIN% add .
    %GIT_BIN% status
    %GIT_BIN% commit -m "feat: AirSense-v2 live cloud deployment, scheduler, and dual-routing bridge"
    echo Git repository initialized and current state committed!
) else (
    echo [INFO] Git binary not available in host environment. Repository structure ready for Cloud Blueprint sync.
)

if defined GH_BIN (
    echo.
    echo Checking GitHub CLI status...
    %GH_BIN% auth status
    echo Attempting GitHub repository sync / check...
    %GH_BIN% repo view AirSense-v2 || %GH_BIN% repo create AirSense-v2 --public --source=. --push
) else (
    echo [INFO] GitHub CLI not installed or not in PATH.
)

echo Sync helper complete.
