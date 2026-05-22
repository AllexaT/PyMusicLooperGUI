@echo off
setlocal

:: Set Console Code Page to UTF-8
chcp 65001 > nul

echo.
echo  __  __           _      _                              
echo ^|  \/  ^|_   _ ___^(_) ___^| ^|     ___   ___  _ __   ___ _ __ 
echo ^| ^|\/^| ^| ^| ^| / __^| ^|/ __^| ^|    / _ \ / _ \^| '_ \ / _ \ '__^|
echo ^| ^|  ^| ^| ^|_^| \__ \ ^| (__^| ^|___^| (_) ^| (_) ^| ^|_) ^|  __/ ^|   
echo ^|_^|  ^|_^|\__,_^|___/_^|\___^|______\___/ \___/^| .__/ \___^|_^|   
echo                                           ^|_^|            
echo.
echo [Starting Music Looper with uv...]

:: Check if uv is installed
where uv >nul 2>nul
if errorlevel 1 (
    echo Command 'uv' not found. Please install it first.
    pause
    exit /b 1
)

:: Run the application
uv run python src/__main__.py

if errorlevel 1 (
    echo.
    echo Application exited with error code %errorlevel%.
    pause
)
