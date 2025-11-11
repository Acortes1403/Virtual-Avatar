@echo off
REM Script para ejecutar ambos servidores de emociones
REM Puerto 8000: Face Detection (YOLOv8)
REM Puerto 8001: Audio Emotion (Whisper)

echo ========================================
echo 🚀 Starting Dual Emotion Servers
echo 📸 Port 8000: Face Detection (YOLOv8)
echo 🎵 Port 8001: Audio Emotion (Whisper)
echo ========================================

REM Navegar al directorio del script
cd /d "%~dp0"

REM Verificar que existe el entorno virtual
if not exist ".venv\Scripts\activate.bat" (
    echo ❌ Error: No se encontró el entorno virtual en .venv
    echo Por favor ejecuta: python -m venv .venv
    pause
    exit /b 1
)

REM Activar entorno virtual
call .venv\Scripts\activate.bat

REM Verificar que Python puede importar la aplicación
python -c "from app.face_server import app; from app.audio_server import app" 2>nul
if errorlevel 1 (
    echo ❌ Error: No se pueden importar las aplicaciones
    echo Instalando dependencias...
    pip install -r requirements.txt
)

echo.
echo ✅ Iniciando servidores...
echo.

REM Crear archivos temporales para los logs
set FACE_LOG=face_server.log
set AUDIO_LOG=audio_server.log

REM Iniciar servidor de Face Detection en puerto 8000
echo 📸 Iniciando Face Detection Server (puerto 8000)...
start "Face Detection Server" cmd /k "call .venv\Scripts\activate.bat && python -m uvicorn app.face_server:app --host 0.0.0.0 --port 8000 --reload"

REM Esperar 3 segundos
timeout /t 3 /nobreak >nul

REM Iniciar servidor de Audio Emotion en puerto 8001
echo 🎵 Iniciando Audio Emotion Server (puerto 8001)...
start "Audio Emotion Server" cmd /k "call .venv\Scripts\activate.bat && python -m uvicorn app.audio_server:app --host 0.0.0.0 --port 8001 --reload"

echo.
echo ✅ Ambos servidores iniciados!
echo.
echo 📖 Face Detection API docs: http://localhost:8000/docs
echo 🎵 Audio Emotion API docs: http://localhost:8001/docs
echo.
echo 💡 Tip: Para detener los servidores, cierra ambas ventanas de comando
echo.
pause