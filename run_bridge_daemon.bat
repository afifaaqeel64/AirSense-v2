@echo off
setlocal
echo ======================================================================
echo    AirSense Pakistan: 24/7 Hardware Serial Bridge Daemon Supervisor   
echo ======================================================================

set PORT_ARG=%~1
if "%PORT_ARG%"=="" (
    echo [DAEMON] No COM port specified. Using automatic dynamic port detection...
    set TARGET_CMD=py -u scripts\airsense_serial_live_bridge.py AUTO
) else (
    echo [DAEMON] Explicit COM port target provided: %PORT_ARG%
    set TARGET_CMD=py -u scripts\airsense_serial_live_bridge.py %PORT_ARG%
)

:loop
echo.
echo [DAEMON] Launching AirSense Serial-to-Cloud Bridge (%TARGET_CMD%)...
%TARGET_CMD%
echo [DAEMON] Bridge exited with code %errorlevel%. Auto-recovering in 2 seconds...
timeout /t 2 /nobreak > nul
goto loop
