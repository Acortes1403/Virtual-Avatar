# 🚀 Dual Emotion Servers Setup

Configuración de servidores separados para evitar conflictos de recursos entre Face Detection y Audio Emotion processing.

## 📋 Arquitectura

### 🎯 **Puerto 8000 - Face Detection Server**
- **Propósito**: Procesamiento de emociones faciales con YOLOv8
- **Endpoints**:
  - `POST /emotion/from-frame` - Detectar emociones en imágenes
  - `GET /health` - Health check
  - `GET /pepper/state` - Estado de Pepper
- **Archivo**: `app/face_server.py`
- **Router**: `app/routers/face_only.py`

### 🎵 **Puerto 8001 - Audio Emotion Server**
- **Propósito**: Procesamiento de emociones de audio con Whisper
- **Endpoints**:
  - `POST /emotion/from-audio` - Emoción desde audio (ASR + texto + SER)
  - `POST /emotion/from-audio-whisper` - Emoción con modelo Whisper especializado
  - `GET /health` - Health check
  - `GET /pepper/state` - Estado de Pepper
- **Archivo**: `app/audio_server.py`
- **Router**: `app/routers/audio_only.py`

## 🚀 **Cómo iniciar los servidores**

### Opción 1: Script de Windows (Recomendado)
```bash
# Ejecutar el script batch
./start_servers.bat
```

### Opción 2: Manualmente
```bash
# Terminal 1: Face Detection Server
python -m uvicorn app.face_server:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Audio Emotion Server
python -m uvicorn app.audio_server:app --host 0.0.0.0 --port 8001 --reload
```

### Opción 3: Script Python
```bash
python start_dual_servers.py
```

## 🔧 **Configuración del Frontend**

Los hooks del frontend se han modificado automáticamente para usar los puertos correctos:

### Face Detection (Puerto 8000)
- `useFaceYolo.jsx` → `http://localhost:8000/emotion/from-frame`

### Audio Emotion (Puerto 8001)
- `useWhisperAudioEmotion.jsx` → `http://localhost:8001/emotion/from-audio-whisper`
- `useAudioEmotionRecorder.jsx` → `http://localhost:8001/emotion/from-audio`
- `useEmotionStream.jsx` → `http://localhost:8001/emotion/from-audio`

## ✅ **Beneficios de la separación**

1. **🚀 Mejor rendimiento**: Sin contención de recursos entre modelos ML
2. **🛡️ Mayor estabilidad**: Si un servidor falla, el otro continúa funcionando
3. **📊 Debugging más fácil**: Logs separados por servicio
4. **⚡ Escalabilidad**: Cada servidor puede configurarse independientemente

## 📖 **API Documentation**

Una vez iniciados los servidores:

- **Face Detection API**: http://localhost:8000/docs
- **Audio Emotion API**: http://localhost:8001/docs

## 🐛 **Troubleshooting**

### Problema: Puerto ya en uso
```bash
# Verificar qué proceso usa el puerto
netstat -ano | findstr :8000
netstat -ano | findstr :8001

# Terminar proceso por PID
taskkill /PID <PID> /F
```

### Problema: Importación fallida
```bash
# Reinstalar dependencias
pip install -r requirements.txt
```

### Problema: Frontend no conecta
1. Verificar que ambos servidores estén ejecutándose
2. Verificar que no hay errores CORS en la consola del navegador
3. Verificar las URLs en los hooks del frontend

## 🔄 **Migración desde servidor único**

Si tenías el servidor anterior funcionando:

1. **Detener** el servidor anterior en puerto 8000
2. **Ejecutar** el nuevo setup con `start_servers.bat`
3. **Verificar** que el frontend conecta correctamente
4. **Opcional**: Hacer backup del `main.py` original si necesitas rollback

## 📝 **Logs**

Los logs se mantienen separados por servidor:
- Face Detection: Prefijo `face-emotion`
- Audio Emotion: Prefijo `audio-emotion`