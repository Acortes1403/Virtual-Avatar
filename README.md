# Virtual Avatar - Sistema de Detección Emocional Multimodal

Sistema de detección de emociones en tiempo real que combina análisis facial (YOLOv8) y análisis de voz (LSTM) mediante fusión multimodal 2oo2, diseñado para controlar el robot humanoide Pepper.

## Descripción General

Este proyecto implementa un sistema completo de videollamada con detección emocional que:
- Detecta emociones faciales mediante YOLOv8
- Analiza emociones en el habla usando LSTM entrenado con CREMA-D
- Fusiona ambas modalidades usando algoritmo 2oo2 (2-out-of-2)
- Envía comandos al robot Pepper para ejecutar animaciones emotivas correspondientes

## Arquitectura del Sistema

El proyecto está compuesto por 4 componentes principales:

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────┐
│  pepper_connect │ ───> │   emotion_api    │ ───> │   Pepper    │
│   (Frontend)    │      │    (Backend)     │      │   Robot     │
│   React + Vite  │      │  Python FastAPI  │      │             │
└─────────────────┘      └──────────────────┘      └─────────────┘
         │                        ▲
         │                        │
         └────────> webrtc_api ───┘
                   (WebRTC Server)
```

### Componentes

1. **emotion_api**: Backend FastAPI con modelos de IA (YOLOv8, LSTM) y sistema de fusión
2. **pepper_connect**: Frontend React para videollamada y visualización
3. **webrtc_api**: Servidor de señalización WebRTC
4. **proxy**: Proxy opcional para comunicación con Pepper

### Carpetas Adicionales (Externas al Proyecto Principal)

- **face-yolo/**: Scripts para entrenar modelos de detección facial con YOLOv8
- **audio-train/**: Scripts para entrenar modelos LSTM de emoción de voz
- **datasets/**: Conjuntos de datos para entrenamiento
- **Gestures/**: Ejemplos de animaciones y guía para controlar el robot Pepper

Estas carpetas son útiles si deseas entrenar nuevos modelos o explorar cómo controlar el robot Pepper.

## Requisitos Previos

### Software Requerido

- **Python**: 3.9 o superior
- **Node.js**: 18.x o superior
- **npm**: 9.x o superior
- **Git**: Para clonar el repositorio

### Hardware Recomendado

- **CPU**: 4 núcleos o más
- **RAM**: 8 GB mínimo (16 GB recomendado)
- **GPU**: Opcional pero mejora el rendimiento de YOLOv8
- **Cámara y micrófono**: Para captura en tiempo real

### Dependencias del Sistema
pepper password: M1rai1nnovation

#### Windows
```bash
# FFmpeg (necesario para procesamiento de audio)
# Descargar desde: https://ffmpeg.org/download.html
# O instalar con Chocolatey:
choco install ffmpeg
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip ffmpeg portaudio19-dev
```

#### macOS
```bash
brew install ffmpeg portaudio
```

## Instalación

### 1. Clonar el Repositorio

```bash
git clone https://github.com/Acortes1403/Virtual-Avatar.git
cd Virtual-Avatar
```

### 2. Configurar Backend (emotion_api)

#### Crear Entorno Virtual

```bash
cd emotion_api
python -m venv .venv
```

#### Activar Entorno Virtual

**Windows:**
```bash
.venv\Scripts\activate
```

**Linux/macOS:**
```bash
source .venv/bin/activate
```

#### Instalar Dependencias

```bash
pip install -r requirements.txt
```

#### Descargar Modelos de IA

Los modelos deben estar en `emotion_api/app/models/`:
- `yolov8_emotions.pt` - Modelo YOLOv8 para detección facial
- `lstm_crema_d_v3.h5` - Modelo LSTM para análisis de voz

**Nota**: Si no tienes los modelos, puedes entrenarlos usando las carpetas `face-yolo/` y `audio-train/`.

#### Configurar Variables de Entorno

Crea o edita el archivo `emotion_api/.env`:

```ini
# === Pepper Configuration ===
PEPPER_EMOTION_ENDPOINT=http://localhost:7070/pepper/emotion

# === Face Detection ===
FACE_EMOTION_ONNX=app/models/face_fer_best.onnx
FACE_IMG_SIZE=640
FACE_DEVICE=cpu
FACE_CONF_THRES=0.05

# === Fusion Configuration ===
FUSION_BASE_AUDIO_WEIGHT=0.45
FUSION_BASE_FACE_WEIGHT=0.55
FUSION_WEIGHT_ADJUSTMENT_MODE=threshold
FUSION_MIN_CONFIDENCE=0.30
FUSION_BOOST_CONSENSUS=true
FUSION_DEBUG_MODE=true
```

### 3. Configurar Frontend (pepper_connect)

```bash
cd pepper_connect
npm install
```

#### Configurar Variables de Entorno

Crea o edita el archivo `pepper_connect/.env`:

```ini
# === Network ===
VITE_SIGNALING_URL=http://localhost:8080

# === Emotion API ===
VITE_EMOTION_API_URL=http://localhost:8000
VITE_AUDIO_API_URL=http://localhost:8000
VITE_FACE_API=http://localhost:8000

# === Face Detection ===
VITE_FACE_ROUTE=/emotion/from-frame
VITE_FACE_INTERVAL_MS=12000
VITE_FACE_IMG_SIZE=640

# === Pepper Configuration ===
VITE_PEPPER_IP=192.168.10.104
VITE_PEPPER_PORT=8070
VITE_PEPPER_PROXY_URL=http://localhost:7070
```

**Nota**: Ajusta `VITE_PEPPER_IP` a la IP de tu robot Pepper.

### 4. Configurar WebRTC Server

```bash
cd webrtc_api
npm install
```

Crea o edita el archivo `webrtc_api/.env`:

```ini
PORT=8080
```

### 5. Configurar Proxy (Opcional)

```bash
cd proxy
npm install
```

Crea o edita el archivo `proxy/.env`:

```ini
PEPPER_IP=192.168.10.104
PEPPER_PORT=8070
PROXY_PORT=7070
```

## Ejecución del Sistema

El sistema requiere ejecutar múltiples servidores. Se recomienda usar terminales separadas para cada uno.

### Terminal 1: Backend (emotion_api)

```bash
cd emotion_api
# Activar entorno virtual
.venv\Scripts\activate  # Windows
# o
source .venv/bin/activate  # Linux/macOS

# Iniciar servidor
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

El backend estará disponible en: `http://localhost:8000`
Documentación API: `http://localhost:8000/docs`

### Terminal 2: WebRTC Server

```bash
cd webrtc_api
npm start
```

Servidor WebRTC: `http://localhost:8080`

### Terminal 3: Proxy (Opcional pero recomendado)

```bash
cd proxy
node proxy-pepper.cjs
```

Proxy: `http://localhost:7070`

### Terminal 4: Frontend

```bash
cd pepper_connect
npm run dev
```

Frontend: `http://localhost:5173`

### Acceder a la Aplicación

Abre tu navegador y ve a:
```
http://localhost:5173/videocall?room=test
```

El parámetro `room` te permite crear diferentes salas de videollamada.

## Uso del Sistema

### Flujo de Operación

1. **Inicio de sesión**: Accede a la URL con un nombre de sala
2. **Permisos**: El navegador solicitará permisos de cámara y micrófono
3. **Detección automática**: El sistema comienza a detectar emociones:
   - Análisis facial cada 300-12000ms (configurable)
   - Análisis de voz cuando detecta habla
4. **Fusión**: El sistema fusiona ambas modalidades cada 1 segundo
5. **Control de Pepper**: La emoción fusionada se envía al robot Pepper automáticamente

### Emociones Detectadas

El sistema detecta 7 emociones básicas:
- **Happy** (Feliz)
- **Sad** (Triste)
- **Angry** (Enojado)
- **Surprise** (Sorpresa)
- **Fear** (Miedo)
- **Disgust** (Disgusto)
- **Neutral** (Neutral)

## Estructura del Proyecto

```
VirtualAvatar/
├── emotion_api/              # Backend FastAPI
│   ├── app/
│   │   ├── main.py          # Aplicación principal
│   │   ├── config.py        # Configuración
│   │   ├── state.py         # Estado global (buffers)
│   │   ├── routers/
│   │   │   ├── emotion.py   # Endpoints de detección
│   │   │   ├── fusion.py    # Endpoints de fusión
│   │   │   └── services/    # Servicios (YOLOv8, LSTM, fusión)
│   │   └── models/          # Modelos de IA (.pt, .h5)
│   ├── requirements.txt
│   └── .env
│
├── pepper_connect/           # Frontend React
│   ├── src/
│   │   ├── pages/
│   │   │   └── VideoCall.jsx
│   │   ├── hooks/           # Hooks para detección
│   │   │   ├── useFaceYolo.jsx
│   │   │   ├── useSpeechEmotion.jsx
│   │   │   └── useEmotionFusion.jsx
│   │   └── lib/             # Utilidades
│   ├── package.json
│   └── .env
│
├── webrtc_api/              # Servidor WebRTC
│   ├── server.js
│   ├── package.json
│   └── .env
│
├── proxy/                   # Proxy para Pepper
│   ├── proxy-pepper.cjs
│   ├── package.json
│   └── .env
│
├── paper/                   # Documentación académica
├── ARCHITECTURE.md          # Documentación detallada
└── README.md               # Este archivo
```

## Configuración Avanzada

### Ajustar Intervalos de Detección

**Frontend** (`pepper_connect/.env`):
```ini
# Detección facial más frecuente (cada 300ms)
VITE_FACE_INTERVAL_MS=300

# Detección facial menos frecuente (cada 12s)
VITE_FACE_INTERVAL_MS=12000
```

### Ajustar Pesos de Fusión

**Backend** (`emotion_api/.env`):
```ini
# Dar más peso a la detección facial
FUSION_BASE_FACE_WEIGHT=0.60
FUSION_BASE_AUDIO_WEIGHT=0.40

# Dar más peso a la detección de audio
FUSION_BASE_FACE_WEIGHT=0.40
FUSION_BASE_AUDIO_WEIGHT=0.60
```

### Modo Debug

**Backend** (`emotion_api/.env`):
```ini
FUSION_DEBUG_MODE=true
FUSION_LOG_ALL_FUSIONS=true
```

Esto generará logs detallados de todas las detecciones y fusiones.

## Solución de Problemas

### Backend no inicia

**Error**: `ModuleNotFoundError: No module named 'X'`

**Solución**:
```bash
cd emotion_api
.venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend no conecta con Backend

**Error**: `Network Error` o `CORS Error`

**Solución**: Verifica que:
1. El backend esté corriendo en `http://localhost:8000`
2. Las URLs en `pepper_connect/.env` sean correctas
3. No haya firewall bloqueando las conexiones

### No se detectan emociones

**Problema**: No aparecen detecciones en la interfaz

**Solución**:
1. Verifica los permisos de cámara/micrófono en el navegador
2. Revisa la consola del navegador (F12) para errores
3. Verifica que los modelos estén en `emotion_api/app/models/`
4. Revisa los logs del backend

### Pepper no responde

**Problema**: Las emociones se detectan pero Pepper no reacciona

**Solución**:
1. Verifica que Pepper esté encendido y conectado a la red
2. Haz ping a la IP de Pepper: `ping 192.168.10.104`
3. Verifica que el proxy esté corriendo
4. Revisa las configuraciones de IP en los archivos `.env`

### Modelos no encontrados

**Error**: `FileNotFoundError: models/yolov8_emotions.pt`

**Solución**:
- Los modelos deben estar en `emotion_api/app/models/`
- Si no los tienes, consulta las carpetas `face-yolo/` y `audio-train/` para entrenar nuevos modelos
- O contacta al administrador del proyecto para obtener los modelos pre-entrenados

## API Endpoints

### Detección de Emociones

#### POST `/emotion/from-frame`
Detecta emoción desde una imagen

**Request:**
```bash
curl -X POST "http://localhost:8000/emotion/from-frame" \
  -F "image=@frame.jpg" \
  -F "room=test"
```

**Response:**
```json
{
  "label": "happy",
  "score": 0.92,
  "room": "test"
}
```

#### POST `/emotion/from-speech`
Detecta emoción desde audio

**Request:**
```bash
curl -X POST "http://localhost:8000/emotion/from-speech" \
  -F "audio=@speech.wav" \
  -F "room=test"
```

**Response:**
```json
{
  "label": "angry",
  "score": 0.91,
  "model": "lstm-crema-v3"
}
```

### Fusión Multimodal

#### POST `/fusion/auto-fuse`
Fusiona las últimas detecciones de rostro y voz

**Request:**
```bash
curl -X POST "http://localhost:8000/fusion/auto-fuse?room=test"
```

**Response:**
```json
{
  "emotion": "angry",
  "confidence": 0.85,
  "strategy": "weighted_fusion",
  "weights": {
    "face": 0.45,
    "audio": 0.55
  }
}
```

#### GET `/fusion/buffer-stats`
Obtiene estadísticas del buffer de emociones

**Request:**
```bash
curl "http://localhost:8000/fusion/buffer-stats?room=test"
```

**Response:**
```json
{
  "room": "test",
  "face_count": 1,
  "audio_count": 1,
  "has_both": true
}
```

## Desarrollo

### Agregar Nuevas Emociones

1. Entrena un nuevo modelo con las emociones deseadas
2. Actualiza el mapeo en `emotion_api/app/routers/services/mapping.py`
3. Actualiza el frontend para mostrar las nuevas emociones

### Modificar el Sistema de Fusión

El algoritmo de fusión está en:
```
emotion_api/app/routers/services/fusion_voting.py
```

Puedes ajustar:
- Pesos de las modalidades
- Estrategias de fusión
- Umbrales de confianza

## Documentación Adicional

- **ARCHITECTURE.md**: Documentación técnica detallada del sistema
- **paper/**: Documentación académica y diagramas
- **Gestures/**: Guía para controlar animaciones del robot Pepper

## Tecnologías Utilizadas

### Backend
- Python 3.11
- FastAPI
- PyTorch (YOLOv8)
- TensorFlow/Keras (LSTM)
- Librosa (procesamiento de audio)
- OpenCV (procesamiento de imágenes)

### Frontend
- React 19
- Vite
- TailwindCSS
- MediaPipe
- Socket.io-client

### IA/ML
- YOLOv8 (Ultralytics)
- LSTM entrenado con CREMA-D
- Algoritmo de fusión 2oo2 custom

## Licencia

Copyright © 2025. Todos los derechos reservados.

Este proyecto es privado y propietario. No está permitido el uso, copia, modificación o distribución sin autorización expresa del autor.

## Contacto

**Amhed Jahir Cortes Lopez**

- **Correo Personal**: ajclrakirute@gmail.com
- **Correo Institucional**: a00835822@tec.mx
- **LinkedIn**: [linkedin.com/in/amhed-jahir-cortes-lopez-03b9322a3](https://www.linkedin.com/in/amhed-jahir-cortes-lopez-03b9322a3)

## Contribuciones

Las contribuciones son bienvenidas, pero con previa validación y aprobación de parte de **Mirai Innovation Research Institute**.

Para contribuir:
1. Haz fork del proyecto en [GitHub](https://github.com/Acortes1403/Virtual-Avatar)
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request con una descripción detallada de los cambios propuestos

**Nota**: Todas las contribuciones serán revisadas por el equipo del Mirai Innovation Research Institute antes de ser aceptadas.

## Notas Importantes

- Este proyecto está diseñado específicamente para el robot Pepper
- Los modelos de IA requieren recursos computacionales significativos
- Se recomienda usar GPU para mejor rendimiento en producción
- El sistema requiere buena iluminación para detección facial óptima
- La calidad del micrófono afecta la precisión de la detección de voz
