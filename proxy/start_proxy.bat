@echo off
echo 🚀 Starting Pepper Proxy Server...
echo.
echo Configuration:
echo   PEPPER_TARGET: %PEPPER_TARGET%
echo   PORT: %PORT%
echo.

cd /d "%~dp0"

REM Set default values if not set
if not defined PEPPER_TARGET set PEPPER_TARGET=http://192.168.10.129:8070
if not defined PORT set PORT=7070

echo Using PEPPER_TARGET: %PEPPER_TARGET%
echo Using PORT: %PORT%
echo.

node proxy-pepper.cjs