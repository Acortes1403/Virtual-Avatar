#!/usr/bin/env python3
"""
Script para ejecutar ambos servidores de emociones de forma separada:
- Puerto 8000: Face Detection (YOLOv8) - Servidor principal
- Puerto 8001: Audio Emotion (Whisper) - Servidor de audio
"""

import subprocess
import sys
import time
import signal
import os
from pathlib import Path

def main():
    # Asegurar que estamos en el directorio correcto
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    print("🚀 Starting dual emotion servers...")
    print("📸 Port 8000: Face Detection (YOLOv8)")
    print("🎵 Port 8001: Audio Emotion (Whisper)")
    print("=" * 50)

    processes = []

    try:
        # Servidor 1: Face Detection (puerto 8000)
        print("Starting Face Detection server on port 8000...")
        face_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn",
            "app.face_server:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ], cwd=script_dir)
        processes.append(("Face Detection", face_process))

        # Esperar un poco antes de iniciar el segundo servidor
        time.sleep(3)

        # Servidor 2: Audio Emotion (puerto 8001)
        print("Starting Audio Emotion server on port 8001...")
        audio_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn",
            "app.audio_server:app",
            "--host", "0.0.0.0",
            "--port", "8001",
            "--reload"
        ], cwd=script_dir)
        processes.append(("Audio Emotion", audio_process))

        print("\n✅ Both servers started successfully!")
        print("📖 Face Detection API docs: http://localhost:8000/docs")
        print("🎵 Audio Emotion API docs: http://localhost:8001/docs")
        print("\nPress Ctrl+C to stop both servers...")

        # Esperar a que ambos procesos terminen
        while True:
            time.sleep(1)
            # Verificar si algún proceso ha terminado
            for name, process in processes:
                if process.poll() is not None:
                    print(f"⚠️ {name} server has stopped unexpectedly")
                    return

    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")

    except Exception as e:
        print(f"❌ Error starting servers: {e}")

    finally:
        # Terminar todos los procesos
        for name, process in processes:
            if process.poll() is None:
                print(f"Stopping {name} server...")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"Force killing {name} server...")
                    process.kill()
                except Exception as e:
                    print(f"Error stopping {name} server: {e}")

        print("✅ All servers stopped")

if __name__ == "__main__":
    main()