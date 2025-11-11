# 🏗️ Arquitectura del Sistema de Detección Emocional Multimodal

## 📋 Tabla de Contenidos
1. [Descripción General](#descripción-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Backend (Python/FastAPI)](#backend-pythonfastapi)
4. [Frontend (React/Vite)](#frontend-reactvite)
5. [Sistema de Fusión 2oo2](#sistema-de-fusión-2oo2)
6. [Flujos de Datos](#flujos-de-datos)
7. [Modelos de IA](#modelos-de-ia)
8. [Configuración](#configuración)

---

## 📖 Descripción General

Este proyecto implementa un sistema de **detección de emociones multimodal** que combina:
- 👤 **Detección Facial** (YOLOv8) - Análisis de expresiones faciales
- 🎤 **Detección de Voz** (LSTM CREMA-D) - Análisis prosódico del habla
- 🔀 **Fusión 2oo2** - Combinación inteligente de ambas modalidades
- 🤖 **Control de Robot Pepper** - Envío de comandos al robot humanoid

### Caso de Uso Principal
Videollamada en tiempo real donde:
1. Usuario habla frente a cámara
2. Sistema detecta emoción facial + vocal
3. Fusiona ambas detecciones usando algoritmo 2oo2
4. Envía emoción fusionada al robot Pepper
5. Pepper ejecuta animación correspondiente

---

## 🏛️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                          │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────────┐  │
│  │ VideoCall.jsx│  │ useFaceYolo   │  │ useSpeechEmotion    │  │
│  │              │──│ (300ms loops) │  │ (4s audio bursts)   │  │
│  │              │  └───────┬───────┘  └──────────┬──────────┘  │
│  │              │          │                     │              │
│  │              │  ┌───────▼─────────────────────▼──────────┐  │
│  │              │  │ useEmotionFusion (1s polling)          │  │
│  │              │──│ Combina Face + Audio                   │  │
│  └──────────────┘  └───────────────┬────────────────────────┘  │
└────────────────────────────────────┼────────────────────────────┘
                                     │ HTTP Requests
                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND (Python/FastAPI)                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  ENDPOINTS (emotion.py)                                   │   │
│  │  • POST /emotion/from-frame  → YOLOv8 Face Detection     │   │
│  │  • POST /emotion/from-speech → LSTM Audio Detection      │   │
│  └──────────────────┬───────────────────────┬─────────────────  │
│                     │                       │                    │
│  ┌──────────────────▼───────┐  ┌───────────▼──────────────┐    │
│  │  EmotionBuffer           │  │  PepperState             │    │
│  │  ┌────────┬────────┐    │  │  ┌─────────────────┐    │    │
│  │  │ Face   │ Audio  │    │  │  │ proce: 0|1      │    │    │
│  │  │ Buffer │ Buffer │    │  │  │ (busy|available)│    │    │
│  │  └────────┴────────┘    │  │  └─────────────────┘    │    │
│  └──────────────────────────┘  └──────────────────────────┘    │
│                     │                                            │
│  ┌──────────────────▼───────────────────────────────────────┐  │
│  │  FUSION SYSTEM (fusion.py + fusion_voting.py)            │  │
│  │  • POST /fusion/auto-fuse  → Combina Face + Audio        │  │
│  │  • GET  /fusion/buffer-stats → Estado del buffer         │  │
│  │  • Sistema de votación 2oo2 con pesos dinámicos          │  │
│  └───────────────────────────────┬──────────────────────────┘  │
└────────────────────────────────────┼────────────────────────────┘
                                     │ HTTP POST
                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ROBOT PEPPER                                │
│  • Recibe emoción mapeada (7 emociones básicas)                 │
│  • Ejecuta animación correspondiente                             │
│  • Actualiza estado proce (0=ocupado, 1=disponible)             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🐍 Backend (Python/FastAPI)

### Estructura de Archivos

```
emotion_api/
├── app/
│   ├── main.py                    # Aplicación FastAPI principal
│   ├── config.py                  # Configuración (carga .env)
│   ├── state.py                   # Estado global (buffer, pepper)
│   │
│   ├── routers/
│   │   ├── emotion.py             # 👤🎤 Endpoints de detección
│   │   ├── fusion.py              # 🔀 Endpoints de fusión
│   │   │
│   │   └── services/
│   │       ├── yolov8_face_emotion.py        # Modelo facial
│   │       ├── lstm_crema_emotion.py         # Modelo de audio
│   │       ├── fusion_voting.py              # Lógica 2oo2
│   │       ├── mapping.py                    # Mapeo emociones
│   │       └── pepper_client.py              # Cliente Pepper
│   │
│   └── models/
│       ├── yolov8_emotions.pt                # Pesos YOLOv8
│       └── lstm_crema_d_v3.h5               # Pesos LSTM
│
├── requirements.txt
└── .env                           # Variables de entorno
```

### Componentes Principales

#### 1. **emotion.py** - Endpoints de Detección

**`POST /emotion/from-frame`**
```python
# FUNCIÓN: Detecta emoción facial desde imagen
# ENTRADA:
#   - image: File (JPEG/PNG)
#   - size: int (opcional, default 640)
#   - room: str (opcional, ID de sala)
# SALIDA:
#   {
#     "label": "happy",
#     "score": 0.92,
#     "scores": [{...}],
#     "room": "test"
#   }
# FLUJO:
#   1. Convierte imagen a numpy array BGR
#   2. Ejecuta YOLOv8 para detectar rostro + emoción
#   3. Guarda resultado en EmotionBuffer.add_face()
#   4. Retorna resultado al frontend
```

**`POST /emotion/from-speech`**
```python
# FUNCIÓN: Detecta emoción desde audio
# ENTRADA:
#   - audio: File (WebM/WAV/MP3)
#   - room: str (opcional)
# SALIDA:
#   {
#     "label": "angry",
#     "score": 0.91,
#     "model": "lstm-crema-v3",
#     "mapped_emotion": "angry",
#     "pepper": {"ok": true}
#   }
# FLUJO:
#   1. Verifica si Pepper está disponible (proce==1)
#   2. Convierte audio a WAV 16kHz mono con ffmpeg
#   3. Ejecuta LSTM CREMA-D para clasificar
#   4. Guarda en EmotionBuffer.add_audio()
#   5. Mapea emoción para Pepper (map_to_face7)
#   6. Envía comando a Pepper
#   7. Retorna resultado
```

#### 2. **fusion.py** - Sistema de Fusión

**`POST /fusion/auto-fuse`**
```python
# FUNCIÓN: Fusiona últimas detecciones de face y audio
# ENTRADA:
#   - room: str (ID de sala)
# SALIDA:
#   {
#     "emotion": "angry",
#     "confidence": 0.85,
#     "strategy": "weighted_fusion",
#     "weights": {"face": 0.45, "audio": 0.55},
#     "face": {...},
#     "audio": {...}
#   }
# FLUJO:
#   1. Obtiene últimas detecciones del buffer
#   2. Verifica que haya datos de AMBAS modalidades
#   3. Ejecuta algoritmo 2oo2 (fusion_voting.py)
#   4. Retorna emoción fusionada
```

**`GET /fusion/buffer-stats`**
```python
# FUNCIÓN: Obtiene estado del buffer de emociones
# ENTRADA:
#   - room: str (opcional)
# SALIDA:
#   {
#     "room": "test",
#     "face_count": 1,
#     "audio_count": 1,
#     "has_both": true
#   }
# USO: Frontend verifica si hay datos antes de llamar auto-fuse
```

#### 3. **state.py** - Estado Global

```python
class EmotionBuffer:
    """
    Buffer temporal de detecciones para fusión multimodal

    PROPÓSITO:
        Almacenar últimas detecciones de face y audio por sala
        Permite que /fusion/auto-fuse obtenga datos recientes

    ESTRUCTURA:
        {
          "test": {  # room ID
            "face": [  # Lista de detecciones faciales
              {"label": "happy", "score": 0.9, "timestamp": 123.45},
              ...
            ],
            "audio": [  # Lista de detecciones de audio
              {"label": "angry", "score": 0.8, "timestamp": 123.50},
              ...
            ]
          }
        }

    MÉTODOS:
        - add_face(room, data): Agregar detección facial
        - add_audio(room, data): Agregar detección de audio
        - get_latest_face(room): Obtener última detección facial
        - get_latest_audio(room): Obtener última detección de audio
        - get_stats(room): Obtener estadísticas del buffer
        - clear_room(room): Limpiar buffer de una sala

    CONFIGURACIÓN:
        - max_age: 10 segundos (detecciones más antiguas se descartan)
        - max_size: 10 detecciones por modalidad por sala
    """

class PepperState:
    """
    Estado del robot Pepper por sala

    PROPÓSITO:
        Evitar enviar comandos cuando Pepper está ocupado
        Coordinar animaciones entre múltiples clientes

    ESTRUCTURA:
        {
          "test": {  # room ID
            "proce": 1,  # 0=ocupado, 1=disponible
            "last_update": 123.45
          }
        }

    MÉTODOS:
        - get_proce(room): Obtener estado actual (0 o 1)
        - set_proce(room, value): Actualizar estado
    """
```

#### 4. **fusion_voting.py** - Algoritmo 2oo2

```python
class EmotionFusionSystem:
    """
    Sistema de fusión multimodal con algoritmo 2oo2

    ALGORITMO 2oo2 (2-out-of-2):
        Requiere concordancia de al menos 2 modalidades de 2
        Si ambas concuerdan → boost de confianza
        Si difieren → pesos dinámicos según confianza

    ESTRATEGIAS:
        1. consensus_weighted: Ambas modalidades de acuerdo
           → Boost de confianza (+10%)
           → Pesos: 50% face, 50% audio

        2. weighted_fusion: Modalidades en conflicto
           → Pesos dinámicos según confianza individual
           → Penalización de confianza (-10%)

        3. face_only: Solo hay detección facial
           → Retorna face con confianza reducida

        4. audio_only: Solo hay detección de audio
           → Retorna audio con confianza reducida

    PESOS DINÁMICOS:
        - Base: face=45%, audio=55%
        - Ajuste por confianza: modalidad más confiada recibe más peso
        - Rango: 30%-70% para evitar dominancia completa

    EJEMPLO:
        Face: happy (0.9)
        Audio: sad (0.7)

        → Estrategia: weighted_fusion (conflicto)
        → Pesos ajustados: face=60%, audio=40% (face más confiada)
        → Resultado: happy (0.78) con penalización
    """
```

---

## ⚛️ Frontend (React/Vite)

### Estructura de Archivos

```
pepper_connect/
├── src/
│   ├── pages/
│   │   └── VideoCall.jsx              # 📹 Página principal
│   │
│   ├── hooks/
│   │   ├── useFaceYolo.jsx            # 👤 Hook detección facial
│   │   ├── useSpeechEmotion.jsx       # 🎤 Hook detección audio
│   │   └── useEmotionFusion.jsx       # 🔀 Hook fusión
│   │
│   ├── lib/
│   │   ├── faceApi.jsx                # API cliente face
│   │   ├── pepperEmotionClient.jsx    # Cliente Pepper
│   │   └── pepperState.jsx            # Estado Pepper
│   │
│   └── .env                            # Configuración
│
└── vite.config.js
```

### Componentes Principales

#### 1. **VideoCall.jsx** - Página Principal

```javascript
/**
 * Componente principal de videollamada
 *
 * RESPONSABILIDADES:
 *   1. Captura video/audio del usuario (getUserMedia)
 *   2. Establece conexión WebRTC con Pepper
 *   3. Coordina hooks de detección (face, audio, fusion)
 *   4. Envía emoción fusionada a Pepper
 *
 * HOOKS USADOS:
 *   - useFaceYolo: Detecta emoción facial cada 300ms
 *   - useSpeechEmotion: Detecta emoción de audio cada 15s
 *   - useEmotionFusion: Fusiona face+audio cada 1s
 *
 * FLUJO:
 *   1. getUserMedia → obtiene stream de cámara/micrófono
 *   2. useFaceYolo captura frames → POST /emotion/from-frame
 *   3. useSpeechEmotion graba audio → POST /emotion/from-speech
 *   4. useEmotionFusion → GET /fusion/buffer-stats
 *                       → POST /fusion/auto-fuse
 *   5. fusedEmotion cambia → triggerPepperEmotion()
 *   6. Pepper ejecuta animación
 *
 * ESTADO:
 *   - userStream: MediaStream del usuario
 *   - fusedEmotion: Emoción fusionada actual
 *   - isAnimating: Si Pepper está animando
 */
```

#### 2. **useFaceYolo.jsx** - Detección Facial

```javascript
/**
 * Hook para detección de emociones faciales con YOLOv8
 *
 * PARÁMETROS:
 *   - videoRef: Ref del elemento <video>
 *   - room: ID de sala
 *
 * RETORNA:
 *   {
 *     label: "happy",      // Emoción detectada
 *     score: 0.92,         // Confianza
 *     ready: true,         // Si está listo
 *     error: null          // Error si hay
 *   }
 *
 * FUNCIONAMIENTO:
 *   1. Loop cada 300ms (configurable con VITE_FACE_INTERVAL_MS)
 *   2. Verifica si Pepper está disponible (isPepperAvailable)
 *   3. Captura frame del video con canvas
 *   4. Convierte a Blob JPEG
 *   5. POST /emotion/from-frame con FormData
 *   6. Aplica smoothing temporal (reduce ruido)
 *   7. Actualiza estado
 *
 * OPTIMIZACIONES:
 *   - Throttling: Solo 1 request a la vez (pendingRequest flag)
 *   - Smoothing: Promedia últimas N detecciones
 *   - Backoff: Reintenta cada 3s si Pepper ocupado
 *   - Timeout: Cancela requests que tardan >5s
 *
 * CONFIGURACIÓN (.env):
 *   VITE_FACE_API=http://localhost:8000
 *   VITE_FACE_INTERVAL_MS=300
 *   VITE_FACE_IMG_SIZE=640
 */
```

#### 3. **useSpeechEmotion.jsx** - Detección de Audio

```javascript
/**
 * Hook para detección de emociones desde audio (LSTM)
 *
 * PARÁMETROS:
 *   - stream: MediaStream del micrófono
 *   - room: ID de sala
 *   - intervalMs: Intervalo entre detecciones (default 15s)
 *   - enabled: Si está habilitado
 *   - onUpdate: Callback cuando detecta emoción
 *
 * FUNCIONAMIENTO:
 *   1. Loop continuo de detección de audio
 *   2. Calcula RMS (loudness) del audio
 *   3. Si RMS > threshold → graba burst de 4 segundos
 *   4. Convierte audio a Blob WebM
 *   5. POST /emotion/from-speech con FormData
 *   6. Llama onUpdate(result)
 *
 * CARACTERÍSTICAS:
 *   - Voice Activity Detection (VAD): Solo procesa si hay voz
 *   - Bursts de 4 segundos: Balance entre latencia y precisión
 *   - Fallback a "neutral" en silencio
 *   - Manejo de estado de Pepper (skip si ocupado)
 *
 * PARÁMETROS DE DETECCIÓN:
 *   - RMS threshold: 0.005 (ajustable)
 *   - Burst duration: 4000ms
 *   - Silence counter: 3 detecciones consecutivas
 *
 * CONFIGURACIÓN:
 *   VITE_AUDIO_API_URL=http://localhost:8000
 */
```

#### 4. **useEmotionFusion.jsx** - Fusión Multimodal

```javascript
/**
 * Hook para fusión de emociones (Face + Audio)
 *
 * PARÁMETROS:
 *   - room: ID de sala
 *   - intervalMs: Intervalo de polling (default 1000ms)
 *   - enabled: Si está habilitado
 *   - onUpdate: Callback cuando hay fusión nueva
 *
 * RETORNA:
 *   {
 *     fusedEmotion: {
 *       emotion: "angry",
 *       confidence: 0.85,
 *       strategy: "weighted_fusion",
 *       weights: {face: 0.45, audio: 0.55}
 *     },
 *     error: null,
 *     performFusion: Function  // Manual trigger
 *   }
 *
 * FLUJO DE FUSIÓN:
 *   1. Polling cada 1 segundo (setInterval)
 *   2. Verifica si Pepper disponible (isPepperAvailable)
 *   3. GET /fusion/buffer-stats
 *   4. Si has_both === true:
 *      → POST /fusion/auto-fuse
 *      → Actualiza fusedEmotion
 *      → Llama onUpdate(data)
 *   5. Si has_both === false:
 *      → Skip, esperar más datos
 *
 * OPTIMIZACIONES:
 *   - isProcessingRef: Evita polling concurrente
 *   - onUpdateRef: Evita recreación de callbacks
 *   - Throttling: Solo muestra logs cada 5s si emoción no cambia
 *
 * CONFIGURACIÓN:
 *   VITE_FACE_API=http://localhost:8000
 */
```

---

## 🔀 Sistema de Fusión 2oo2

### Concepto

El sistema **2-out-of-2 (2oo2)** requiere que al menos 2 de 2 modalidades estén disponibles y concuerden para generar una detección válida.

### Ventajas vs. Unimodal

| Aspecto | Unimodal (Solo Face o Audio) | Multimodal 2oo2 |
|---------|------------------------------|-----------------|
| **Precisión** | 70-80% | 85-95% |
| **Robustez** | Falla con oclusiones/ruido | Compensa debilidades |
| **Confianza** | Variable | Boosted al concordar |
| **Contexto** | Limitado | Rico (visual + prosódico) |

### Estrategias de Fusión

#### 1. **Consensus Weighted** (Consenso)
```
Condición: face.label == audio.label
Acción:
  - Confianza boosted (+10%)
  - Pesos equilibrados (50/50)
Ejemplo:
  Face: happy (0.8)
  Audio: happy (0.7)
  → Resultado: happy (0.825) ✓ boost aplicado
```

#### 2. **Weighted Fusion** (Conflicto)
```
Condición: face.label != audio.label
Acción:
  - Pesos dinámicos según confianza
  - Confianza penalizada (-10%)
Ejemplo:
  Face: happy (0.9)  → peso 60%
  Audio: sad (0.6)   → peso 40%
  → Resultado: happy (0.72) con penalización
```

#### 3. **Face Only** / **Audio Only**
```
Condición: Solo una modalidad disponible
Acción:
  - Usar modalidad disponible
  - Confianza reducida (×0.8)
```

### Pesos Dinámicos

```python
# Configuración base
base_face_weight = 0.45
base_audio_weight = 0.55

# Ajuste por confianza
if face.score > audio.score:
    face_weight += (face.score - audio.score) * 0.5
    audio_weight -= (face.score - audio.score) * 0.5

# Límites
face_weight = clamp(face_weight, 0.30, 0.70)
audio_weight = clamp(audio_weight, 0.30, 0.70)

# Normalización
total = face_weight + audio_weight
face_weight /= total
audio_weight /= total
```

---

## 📊 Flujos de Datos

### Flujo Completo de Detección

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. CAPTURA (Frontend)                                            │
│    - getUserMedia → MediaStream                                  │
│    - Video: 640x480 @ 15fps                                      │
│    - Audio: 48kHz stereo                                         │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                ┌──────────┴────────┐
                │                   │
                ▼                   ▼
┌───────────────────────┐  ┌────────────────────────┐
│ 2A. FACE DETECTION    │  │ 2B. AUDIO DETECTION    │
│ (Every 300ms)         │  │ (Every 15s)            │
│                       │  │                        │
│ • Capture frame       │  │ • Detect voice (VAD)   │
│ • Resize to 640x640   │  │ • Record 4s burst      │
│ • Convert to JPEG     │  │ • Convert to WebM      │
│ • POST /from-frame    │  │ • POST /from-speech    │
└─────────┬─────────────┘  └──────────┬─────────────┘
          │                           │
          ▼                           ▼
┌──────────────────────────────────────────────────┐
│ 3. ML MODELS (Backend)                           │
│                                                   │
│ Face: YOLOv8                 Audio: LSTM         │
│ • Detect face bbox           • Extract MFCCs     │
│ • Classify emotion           • Classify emotion  │
│ • Return scores              • Return scores     │
└─────────┬────────────────────────────┬───────────┘
          │                            │
          ▼                            ▼
┌──────────────────────────────────────────────────┐
│ 4. EMOTION BUFFER                                │
│    {                                             │
│      "test": {                                   │
│        "face": [{label:"happy", score:0.9}],    │
│        "audio": [{label:"angry", score:0.8}]    │
│      }                                           │
│    }                                             │
└────────────────────┬─────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────┐
│ 5. FUSION (Every 1s)                             │
│    • GET /buffer-stats                           │
│    • If has_both:                                │
│      → POST /auto-fuse                           │
│      → Apply 2oo2 algorithm                      │
│      → Return fused emotion                      │
└────────────────────┬─────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────┐
│ 6. PEPPER CONTROL                                │
│    • Map emotion (7 basic emotions)              │
│    • Check proce status                          │
│    • If available:                               │
│      → POST http://pepper:8070/trigger           │
│      → Pepper animates                           │
│      → Update proce=0 (busy)                     │
└──────────────────────────────────────────────────┘
```

### Timing Diagram

```
Timeline (ms):
0      300    600    900    1000   1500   4000   15000
│      │      │      │      │      │      │      │
├──────┼──────┼──────┼──────┼──────┼──────┼──────┼─────► Time
│      │      │      │      │      │      │      │
Face:  🔍    🔍    🔍    🔍    🔍    🔍    🔍    🔍
       (detect every 300ms)
                            │             │
Audio:                      🎤──────────────🎤
                           (4s burst)   (detect)
                            │
Fusion:                     🔀            🔀
                          (fuse)       (fuse)
                            │             │
Pepper:                     🤖───────────🤖
                          (animate)    (animate)
                          proce=0→1    proce=0→1
```

---

## 🤖 Modelos de IA

### 1. YOLOv8 Face Emotion

**Archivo**: `app/models/yolov8_emotions.pt`

**Características**:
- Arquitectura: YOLOv8n (nano, optimizado para velocidad)
- Input: Imagen RGB 640x640
- Output: Bounding boxes + clasificación de emoción
- Clases: 7 emociones (happy, sad, angry, surprise, fear, disgust, neutral)
- FPS: ~30-50 en CPU, ~100+ en GPU

**Pipeline de Inferencia**:
```python
# 1. Preprocesamiento
image_resized = cv2.resize(image, (640, 640))

# 2. Inferencia
results = model.predict(image_resized, conf=0.25)

# 3. Postprocesamiento
for detection in results[0].boxes:
    bbox = detection.xyxy
    emotion_id = int(detection.cls)
    confidence = float(detection.conf)

    emotion_label = EMOTION_NAMES[emotion_id]
    # → {"label": "happy", "score": 0.92, "bbox": [...]}
```

### 2. LSTM CREMA-D V3

**Archivo**: `app/models/lstm_crema_d_v3.h5`

**Características**:
- Arquitectura: Bidirectional LSTM
- Dataset: CREMA-D (Crowd-sourced Emotional Multimodal Actors Dataset)
- Input: MFCCs (Mel-Frequency Cepstral Coefficients) del audio
- Output: Probabilidades para 6 emociones
- Clases: angry, sad, happy, fear, disgust, neutral

**Pipeline de Inferencia**:
```python
# 1. Feature Extraction
audio, sr = librosa.load(wav_path, sr=16000)
mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=40)
mfccs_scaled = (mfccs - mean) / std  # Normalización

# 2. Inferencia
predictions = lstm_model.predict(mfccs_scaled)

# 3. Postprocesamiento
emotion_id = np.argmax(predictions)
confidence = float(predictions[0][emotion_id])

# → {"label": "angry", "score": 0.91}
```

---

## ⚙️ Configuración

### Variables de Entorno

#### Backend (`emotion_api/.env`)

```ini
# === FUSION CONFIGURATION ===
# Pesos base para fusión multimodal
FUSION_BASE_AUDIO_WEIGHT=0.55       # Peso de audio (55%)
FUSION_BASE_FACE_WEIGHT=0.45        # Peso de face (45%)

# Modo de ajuste de pesos (threshold | confidence | static)
FUSION_WEIGHT_ADJUSTMENT_MODE=threshold

# Rangos de pesos permitidos
FUSION_MIN_WEIGHT=0.30              # Mínimo 30%
FUSION_MAX_WEIGHT=0.70              # Máximo 70%

# Umbrales de confianza
FUSION_MIN_CONFIDENCE=0.30          # Mínimo para considerar válido
FUSION_STRONG_CONFIDENCE=0.70       # Umbral de confianza "fuerte"

# Boost y penalizaciones
FUSION_BOOST_CONSENSUS=true         # Boost cuando concuerdan
FUSION_CONSENSUS_BOOST=0.10         # +10% al concordar
FUSION_PENALIZE_CONFLICT=true       # Penalizar conflictos
FUSION_CONFLICT_PENALTY=0.10        # -10% en conflicto

# Supresión de neutral
FUSION_SUPPRESS_NEUTRAL=false       # No suprimir neutral
FUSION_NEUTRAL_THRESHOLD=0.50       # Umbral para considerar neutral
FUSION_NEUTRAL_MIN_GAP=0.15         # Gap mínimo vs otras emociones

# Debug
FUSION_DEBUG_MODE=false             # Logs detallados
FUSION_LOG_ALL_FUSIONS=true         # Log de todas las fusiones

# === PEPPER CONFIGURATION ===
PEPPER_IP=192.168.10.104            # IP del robot Pepper
PEPPER_PORT=8070                    # Puerto API de Pepper
```

#### Frontend (`pepper_connect/.env`)

```ini
# === API ENDPOINTS ===
VITE_FACE_API=http://localhost:8000         # Backend face/audio/fusion
VITE_AUDIO_API_URL=http://localhost:8000    # Backend audio (mismo)
VITE_EMOTION_API_URL=http://localhost:8000  # Backend emotion

# === DETECTION INTERVALS ===
VITE_FACE_INTERVAL_MS=300           # Detección facial cada 300ms
VITE_FACE_IMG_SIZE=640              # Tamaño de imagen para YOLOv8

# === PEPPER CONFIGURATION ===
VITE_PEPPER_IP=192.168.10.104       # IP del robot
VITE_PEPPER_PORT=8070               # Puerto API

# === WEBRTC ===
VITE_SIGNALING_URL=http://localhost:8080  # Servidor señalización
```

### Instalación y Ejecución

#### Backend

```bash
# 1. Crear entorno virtual
cd emotion_api
python -m venv .venv

# 2. Activar entorno
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Iniciar servidor
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Acceder a docs: http://localhost:8000/docs
```

#### Frontend

```bash
# 1. Instalar dependencias
cd pepper_connect
npm install

# 2. Iniciar dev server
npm run dev

# Acceder: http://localhost:5173/videocall?room=test
```

#### Proxy (Opcional)

```bash
cd proxy
node start_proxy.bat

# Proxy en: http://localhost:7070
# Redirige a Pepper: http://192.168.10.104:8070
```

---

## 📈 Métricas y Monitoreo

### Logs del Sistema

#### Backend (FastAPI)

```
INFO:     face frame | room=test | size=640 | top1=happy:0.920 | detections=1 | conf_thres=0.25
INFO:     🎤 [SPEECH-CREMA] ✅ Classification completed: angry (0.910)
INFO:     [FUSION] Auto-fusion for room test: angry (0.852) via weighted_fusion
INFO:     🎤 [SPEECH-CREMA] 🤖 Pepper command: angry → angry (sent: True)
```

#### Frontend (Console)

```
[FUSION] Starting fusion system for room: test, interval: 1000ms
👤 [FACE-YOLO] Detected: happy (92%)
🎯 Speech detected: angry (91%)
[FUSION] ✅ Both modalities available (face: 1, audio: 1)
[FUSION] ✨ New fusion: angry (85.2%) via weighted_fusion | weights: face=45% audio=55%
🎭 [FUSION → PEPPER] angry (85.2%) via weighted_fusion | weights: F45% A55%
```

### Endpoints de Debug

```bash
# Estado del buffer
GET http://localhost:8000/fusion/buffer-stats?room=test

# Configuración de fusión
GET http://localhost:8000/fusion/config

# Estado de Pepper
GET http://localhost:8000/pepper/status?room=test

# Limpiar buffer
POST http://localhost:8000/fusion/clear-buffer
```

---

## 🔧 Troubleshooting

### Problema: Face no guarda en buffer

**Síntoma**: `face_count: 0` en buffer-stats

**Solución**:
1. Verificar que `/emotion/from-frame` retorne 200
2. Verificar logs: `👤 [FACE-YOLO] Saved to buffer for room test`
3. Verificar que `room` se envíe en request

### Problema: Fusión nunca se ejecuta

**Síntoma**: No logs de `[FUSION] ✨ New fusion`

**Solución**:
1. Verificar `has_both: true` en buffer-stats
2. Verificar que ambos hooks (face, audio) estén corriendo
3. Verificar que Pepper esté disponible (proce=1)

### Problema: Pepper no responde

**Síntoma**: `pepper: {ok: false}`

**Solución**:
1. Ping a Pepper: `ping 192.168.10.104`
2. Verificar puerto: `curl http://192.168.10.104:8070/video_feed`
3. Verificar firewall

---

## 📚 Referencias

- **YOLOv8**: https://docs.ultralytics.com/
- **CREMA-D Dataset**: https://github.com/CheyneyComputerScience/CREMA-D
- **FastAPI**: https://fastapi.tiangolo.com/
- **React Hooks**: https://react.dev/reference/react
- **WebRTC**: https://webrtc.org/

---

## 👥 Contribuidores

Para contribuir al proyecto, por favor:
1. Lee esta documentación completa
2. Revisa los comentarios en el código
3. Sigue las convenciones de código existentes
4. Prueba tus cambios localmente
5. Documenta nuevas funcionalidades

---

**Versión**: 1.0.0
**Última actualización**: 2025-01-22
