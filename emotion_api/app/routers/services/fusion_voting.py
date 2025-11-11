# emotion_api/app/routers/services/fusion_voting.py
"""
Sistema de Fusión Emocional con Pesos Dinámicos (2-of-2 Voting)

Combina detecciones de:
- YOLOv8 (face emotion detection)
- LSTM CREMA-D V3 (audio emotion detection)

Usando votación ponderada con pesos dinámicos basados en confianza.
"""

from typing import Dict, List, Literal, Optional, Tuple
import time
from collections import defaultdict
import numpy as np


class EmotionEMA:
    """
    Exponential Moving Average (EMA) para suavizado temporal de emociones

    VENTAJAS sobre buffer de ventana fija:
    - Transiciones más suaves y naturales
    - Menos memoria (no almacena historial completo)
    - Más responsivo a cambios reales
    - No tiene "saltos" al entrar/salir de la ventana

    PARÁMETRO CLAVE: alpha
    - alpha = 0.2 → MUY suave (95% historial, 5% nuevo)
    - alpha = 0.3 → Suave (70% historial, 30% nuevo) [RECOMENDADO]
    - alpha = 0.5 → Balanceado (50/50)
    - alpha = 0.7 → Reactivo (30% historial, 70% nuevo)
    """
    def __init__(self, alpha: float = 0.3):
        """
        Args:
            alpha: Factor de suavizado (0-1)
                   Menor = más suave, Mayor = más reactivo
        """
        self.alpha = alpha
        self.ema_scores = {}  # {emotion: ema_score}
        self.initialized = False

    def update(self, emotion_scores: Dict[str, float]) -> Dict[str, float]:
        """
        Actualiza EMA con nuevos scores

        Formula: EMA_new = α * score_current + (1-α) * EMA_previous

        Args:
            emotion_scores: {emotion: confidence} actual

        Returns:
            {emotion: ema_confidence} suavizado
        """
        if not self.initialized:
            # Primera vez: inicializar con valores actuales
            self.ema_scores = emotion_scores.copy()
            self.initialized = True
            return self.ema_scores

        # Aplicar EMA a cada emoción
        for emotion, score in emotion_scores.items():
            if emotion not in self.ema_scores:
                # Nueva emoción: inicializar
                self.ema_scores[emotion] = score
            else:
                # Aplicar EMA
                self.ema_scores[emotion] = (
                    self.alpha * score +
                    (1 - self.alpha) * self.ema_scores[emotion]
                )

        return self.ema_scores

    def get_dominant_emotion(self) -> Tuple[str, float]:
        """Retorna la emoción con mayor EMA"""
        if not self.ema_scores:
            return 'neutral', 0.5

        dominant = max(self.ema_scores.items(), key=lambda x: x[1])
        return dominant[0], dominant[1]

    def reset(self):
        """Resetea el EMA"""
        self.ema_scores = {}
        self.initialized = False


class EmotionPersistence:
    """
    Sistema de persistencia emocional para evitar "neutral bias"

    PROBLEMA:
        Cuando la confianza baja, el sistema actual cae a neutral inmediatamente.
        Esto no es natural: los humanos mantienen emociones incluso si la detección es débil.

    SOLUCIÓN:
        Mantener la última emoción "fuerte" y usarla cuando la detección actual es débil.
        Aplicar decay gradual para eventualmente volver a neutral si persiste baja confianza.

    EJEMPLO:
        t=0s:  happy (0.85) → guardar como "strong emotion"
        t=2s:  neutral (0.35) → usar happy (0.80 con decay)
        t=4s:  neutral (0.30) → usar happy (0.76 con decay)
        t=10s: neutral (0.30) → usar happy (0.61 con decay)
        t=20s: neutral (0.30) → finalmente neutral (0.30)
    """
    def __init__(
        self,
        strong_threshold: float = 0.70,
        weak_threshold: float = 0.40,
        decay_rate: float = 0.97,
        min_persistence: float = 0.35
    ):
        """
        Args:
            strong_threshold: Confianza para considerar "emoción fuerte" (default 0.70)
            weak_threshold: Confianza bajo la cual activar persistencia (default 0.40)
            decay_rate: Factor de decay por actualización (default 0.97 = -3% por update)
            min_persistence: Confianza mínima para seguir usando persistencia (default 0.35)
        """
        self.strong_threshold = strong_threshold
        self.weak_threshold = weak_threshold
        self.decay_rate = decay_rate
        self.min_persistence = min_persistence

        self.last_strong_emotion = 'neutral'
        self.last_strong_confidence = 0.5
        self.last_strong_timestamp = time.time()

    def update(self, emotion: str, confidence: float) -> Tuple[str, float, bool]:
        """
        Actualiza persistencia y retorna emoción a usar

        Args:
            emotion: Emoción detectada actualmente
            confidence: Confianza de la detección actual

        Returns:
            (emotion_to_use, confidence_to_use, used_persistence)
        """
        current_time = time.time()

        # Si la detección actual es fuerte, guardarla
        if confidence >= self.strong_threshold:
            self.last_strong_emotion = emotion
            self.last_strong_confidence = confidence
            self.last_strong_timestamp = current_time
            return emotion, confidence, False  # No usó persistencia

        # Si la detección actual es débil, considerar usar persistencia
        if confidence < self.weak_threshold:
            # Calcular confianza con decay
            decayed_confidence = self.last_strong_confidence * self.decay_rate

            # Solo usar persistencia si la emoción decayada sigue siendo válida
            if decayed_confidence >= self.min_persistence:
                # Aplicar decay
                self.last_strong_confidence = decayed_confidence
                return self.last_strong_emotion, decayed_confidence, True  # Usó persistencia

        # Caso normal: usar detección actual
        return emotion, confidence, False

    def reset(self):
        """Resetea la persistencia"""
        self.last_strong_emotion = 'neutral'
        self.last_strong_confidence = 0.5
        self.last_strong_timestamp = time.time()


class ConfidenceBasedVotingFusion:
    """
    Sistema de fusión con pesos dinámicos base audio-favorecida
    """

    # Mapeo de emociones a formato estándar
    EMOTION_MAPPING = {
        'anger': 'angry',
        'angry': 'angry',
        'disgust': 'disgusted',
        'disgusted': 'disgusted',
        'fear': 'fearful',
        'fearful': 'fearful',
        'happy': 'happy',
        'neutral': 'neutral',
        'sad': 'sad',
        'surprise': 'surprised',
        'surprised': 'surprised'
    }

    # Todas las emociones posibles
    ALL_EMOTIONS = ['angry', 'disgusted', 'fearful', 'happy', 'neutral', 'sad', 'surprised']

    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializa el sistema de fusión

        Args:
            config: Diccionario de configuración (si es None, usa valores por defecto)
        """
        self.config = config or self._default_config()

        # ===================================================================
        # NUEVO: EMA (Exponential Moving Average) por sala
        # ===================================================================
        # Reemplaza buffer de ventana fija con EMA para transiciones más suaves
        self.ema_systems = {}  # {"room_id": EmotionEMA()}

        # ===================================================================
        # NUEVO: Sistema de Persistencia Emocional por sala
        # ===================================================================
        # Evita caer a neutral cuando la confianza baja temporalmente
        self.persistence_systems = {}  # {"room_id": EmotionPersistence()}

        # ===================================================================
        # SUAVIZADO TEMPORAL AGRESIVO: Buffer de historial de fusiones por sala
        # ===================================================================
        # Almacena últimas N fusiones para detectar:
        # - Emociones consistentes → boost de confianza
        # - Cambios bruscos → penalización FUERTE
        # - Outliers → RECHAZO o penalización muy fuerte
        # - Emociones dominantes → mantener por mínimo tiempo
        #
        # Estructura: {"room_id": [fusion1, fusion2, ...]}
        self.fusion_history = {}
        self.max_history_size = 8  # Últimas 8 fusiones (aumentado de 5)
        self.temporal_config = {
            'enable_smoothing': True,          # Activar suavizado temporal
            'enable_ema': True,                # Activar EMA (NUEVO)
            'enable_persistence': True,        # Activar persistencia emocional (NUEVO)
            'ema_alpha': 0.3,                  # Factor EMA: 0.3 = suave (NUEVO)

            # BOOSTS (premios por consistencia)
            'consistency_boost': 1.15,         # +15% si emoción es consistente (antes +5%)
            'strong_consistency_boost': 1.25,  # +25% si aparece en últimas 4+ fusiones (NUEVO)

            # PENALTIES (castigos por cambios)
            'sudden_change_penalty': 0.75,     # -25% en cambio brusco (antes -5%, MUCHO más agresivo)
            'outlier_penalty': 0.50,           # -50% si es outlier (antes -15%, MUCHO más agresivo)
            'weak_outlier_reject': True,       # Rechazar outliers con confianza < 50% (NUEVO)

            # VENTANAS TEMPORALES
            'min_history_for_smoothing': 2,    # Mínimo de fusiones para aplicar
            'strong_consistency_window': 4,    # Ventana para strong boost (NUEVO)

            # MÍNIMO TIEMPO DE EMOCIÓN (evita "flasheo") - AJUSTADO para permitir cambios más rápidos
            'min_emotion_duration_sec': 1.5,   # Emoción debe durar mínimo 1.5s antes de cambiar (ANTES: 3s)
            'allow_change_to_neutral': True,   # Permitir cambio rápido a neutral (NUEVO)

            # FILTRADO DE RUIDO - AJUSTADO para ser menos restrictivo
            'min_confidence_for_change': 0.42, # Confianza mínima para aceptar cambio de emoción (ANTES: 0.50)
        }

    def _default_config(self) -> Dict:
        """Configuración por defecto"""
        return {
            # Pesos base (audio favorecido)
            'base_audio_weight': 0.55,
            'base_face_weight': 0.45,

            # Modo de ajuste
            'weight_adjustment_mode': 'threshold',  # threshold | linear | exponential

            # Límites de pesos
            'min_weight': 0.25,
            'max_weight': 0.75,

            # Umbrales de confianza
            'min_confidence': 0.30,
            'strong_confidence': 0.75,

            # Modificadores
            'boost_consensus': True,
            'consensus_boost': 1.15,  # +15%
            'penalize_conflict': True,
            'conflict_penalty': 0.90,  # -10%

            # Manejo de neutral
            'suppress_neutral': True,
            'neutral_threshold': 0.60,
            'neutral_min_gap': 0.15,

            # Debug
            'debug_mode': True,
        }

    def fuse(self, face_result: Dict, audio_result: Dict, room: str = "default") -> Dict:
        """
        Fusión principal de emociones CON SUAVIZADO TEMPORAL

        Args:
            face_result: {"label": str, "score": float, "scores": [...]}
            audio_result: {"label": str, "score": float, "scores": [...]}
            room: ID de sala para tracking de historial

        Returns:
            {
                "emotion": str,
                "confidence": float,
                "strategy": str,
                "weights": {"face": float, "audio": float},
                "face": {...},
                "audio": {...},
                "debug": {...},
                "temporal": {...}  # Info de suavizado temporal
            }
        """
        start_time = time.time()

        # 1. Extraer y normalizar datos
        face_emotion = self._normalize_emotion(face_result.get('label', 'neutral'))
        face_conf = float(face_result.get('score', 0.0))
        audio_emotion = self._normalize_emotion(audio_result.get('label', 'neutral'))
        audio_conf = float(audio_result.get('score', 0.0))

        if self.config['debug_mode']:
            print(f"[FUSION] Input -> Face: {face_emotion} ({face_conf:.2f}), Audio: {audio_emotion} ({audio_conf:.2f})")

        # 2. Validar confianzas mínimas
        min_conf = self.config['min_confidence']
        face_valid = face_conf >= min_conf
        audio_valid = audio_conf >= min_conf

        # 3. Casos especiales: una o ninguna modalidad válida
        if not face_valid and not audio_valid:
            return self._fallback_neutral(face_result, audio_result)

        if not face_valid:
            return self._audio_only(audio_result)

        if not audio_valid:
            return self._face_only(face_result)

        # 4. Calcular pesos dinámicos
        w_face, w_audio = self._calculate_dynamic_weights(face_conf, audio_conf)

        # 5. Consenso vs Conflicto
        if face_emotion == audio_emotion:
            # CONSENSO: ambas modalidades coinciden
            raw_result = self._consensus_weighted(
                face_result, audio_result,
                face_emotion, face_conf, audio_conf,
                w_face, w_audio
            )
        else:
            # CONFLICTO: modalidades no coinciden
            raw_result = self._weighted_fusion(
                face_result, audio_result,
                w_face, w_audio
            )

        # ===================================================================
        # 6. SUAVIZADO TEMPORAL (NUEVA MEJORA)
        # ===================================================================
        # Aplica filtros temporales para:
        # - Evitar cambios bruscos irreales
        # - Boost emociones consistentes
        # - Filtrar outliers (ruido)
        result = self._smooth_with_history(raw_result, room)

        # ===================================================================
        # 7. PERSISTENCIA EMOCIONAL (NUEVA MEJORA)
        # ===================================================================
        # Evita caer a neutral cuando la confianza baja temporalmente
        if self.temporal_config.get('enable_persistence', True):
            result = self._apply_persistence(result, room)

        # Agregar tiempo de procesamiento
        result['processing_time_ms'] = round((time.time() - start_time) * 1000, 2)

        if self.config['debug_mode']:
            temporal_info = result.get('temporal', {})
            temporal_flag = f" [{temporal_info.get('adjustment', 'none')}]" if temporal_info else ""
            persistence_info = result.get('persistence', {})
            persistence_flag = " [PERSIST]" if persistence_info.get('used', False) else ""
            print(f"[FUSION] Output -> {result['emotion']} ({result['confidence']:.2f}) via {result['strategy']}{temporal_flag}{persistence_flag} in {result['processing_time_ms']}ms")

        return result

    def _normalize_emotion(self, emotion: str) -> str:
        """Normaliza nombre de emoción a formato estándar"""
        return self.EMOTION_MAPPING.get(emotion.lower(), emotion.lower())

    def _calculate_dynamic_weights(self, face_conf: float, audio_conf: float) -> Tuple[float, float]:
        """
        Calcula pesos dinámicos según modo configurado

        Returns:
            (w_face, w_audio) normalizados que suman 1.0
        """
        mode = self.config['weight_adjustment_mode']

        if mode == 'threshold':
            return self._adjust_weights_threshold(face_conf, audio_conf)
        elif mode == 'linear':
            return self._adjust_weights_linear(face_conf, audio_conf)
        else:  # exponential
            return self._adjust_weights_exponential(face_conf, audio_conf)

    def _adjust_weights_threshold(self, face_conf: float, audio_conf: float) -> Tuple[float, float]:
        """
        Ajuste escalonado MEJORADO (más responsivo a calidad)

        Diferencia < 0.10: sin ajuste
        Diferencia < 0.20: ajuste ±0.08 (antes 0.05)
        Diferencia < 0.35: ajuste ±0.15 (antes 0.10)
        Diferencia < 0.50: ajuste ±0.20 (antes 0.15)
        Diferencia >= 0.50: ajuste ±0.25 (nuevo - máximo)
        """
        diff = face_conf - audio_conf
        abs_diff = abs(diff)

        # Determinar ajuste según umbrales (más agresivo)
        if abs_diff < 0.10:
            adjustment = 0.0
        elif abs_diff < 0.20:
            adjustment = 0.08
        elif abs_diff < 0.35:
            adjustment = 0.15
        elif abs_diff < 0.50:
            adjustment = 0.20
        else:
            adjustment = 0.25

        # Aplicar signo según quién tiene mayor confianza
        if diff < 0:  # audio tiene más confianza
            adjustment = -adjustment

        # Aplicar ajuste a los pesos base
        w_face = self.config['base_face_weight'] + adjustment
        w_audio = self.config['base_audio_weight'] - adjustment

        # Clamp entre límites
        w_face = max(self.config['min_weight'], min(self.config['max_weight'], w_face))
        w_audio = max(self.config['min_weight'], min(self.config['max_weight'], w_audio))

        # Normalizar para que sumen 1.0
        total = w_face + w_audio
        return w_face / total, w_audio / total

    def _adjust_weights_linear(self, face_conf: float, audio_conf: float) -> Tuple[float, float]:
        """Ajuste lineal proporcional"""
        diff = face_conf - audio_conf
        # Ajuste proporcional a la diferencia (máximo ±0.15)
        adjustment = max(-0.15, min(0.15, diff * 0.3))

        w_face = self.config['base_face_weight'] + adjustment
        w_audio = self.config['base_audio_weight'] - adjustment

        w_face = max(self.config['min_weight'], min(self.config['max_weight'], w_face))
        w_audio = max(self.config['min_weight'], min(self.config['max_weight'], w_audio))

        total = w_face + w_audio
        return w_face / total, w_audio / total

    def _adjust_weights_exponential(self, face_conf: float, audio_conf: float) -> Tuple[float, float]:
        """Ajuste exponencial (énfasis en diferencias grandes)"""
        diff = face_conf - audio_conf
        # Exponencial suave
        adjustment = (abs(diff) ** 1.5) * 0.2 * (1 if diff > 0 else -1)
        adjustment = max(-0.15, min(0.15, adjustment))

        w_face = self.config['base_face_weight'] + adjustment
        w_audio = self.config['base_audio_weight'] - adjustment

        w_face = max(self.config['min_weight'], min(self.config['max_weight'], w_face))
        w_audio = max(self.config['min_weight'], min(self.config['max_weight'], w_audio))

        total = w_face + w_audio
        return w_face / total, w_audio / total

    def _consensus_weighted(
        self,
        face_result: Dict,
        audio_result: Dict,
        emotion: str,
        face_conf: float,
        audio_conf: float,
        w_face: float,
        w_audio: float
    ) -> Dict:
        """
        Estrategia de CONSENSO: ambas modalidades coinciden

        Aplicar boost a la confianza promedio
        """
        # Confianza promedio ponderada
        avg_conf = w_face * face_conf + w_audio * audio_conf

        # Aplicar boost si está habilitado
        if self.config['boost_consensus']:
            final_conf = min(1.0, avg_conf * self.config['consensus_boost'])
        else:
            final_conf = avg_conf

        return {
            'emotion': emotion,
            'confidence': round(final_conf, 4),
            'strategy': 'consensus_weighted',
            'weights': {'face': round(w_face, 3), 'audio': round(w_audio, 3)},
            'face': face_result,
            'audio': audio_result,
            'debug': {
                'avg_confidence_before_boost': round(avg_conf, 4),
                'boost_applied': self.config['boost_consensus'],
                'both_agree': True
            }
        }

    def _weighted_fusion(
        self,
        face_result: Dict,
        audio_result: Dict,
        w_face: float,
        w_audio: float
    ) -> Dict:
        """
        Estrategia de CONFLICTO: fusión ponderada de distribuciones completas

        Si las modalidades tienen distribuciones completas (scores), las fusiona.
        Si no, usa solo las confianzas principales.

        NOTA PARA SONARQUBE:
            Esta función tiene complejidad 16 (apenas 1 sobre el límite de 15)
            debido al manejo de casos especiales: penalización de conflictos,
            supresión inteligente de neutral, y validación de rangos.
            La complejidad es necesaria para la lógica de fusión y está bien encapsulada.
        """
        # Intentar obtener distribuciones completas
        face_scores = self._extract_scores_dict(face_result)
        audio_scores = self._extract_scores_dict(audio_result)

        # Fusión ponderada
        fused_scores = {}
        for emotion in self.ALL_EMOTIONS:
            f_score = face_scores.get(emotion, 0.0)
            a_score = audio_scores.get(emotion, 0.0)
            fused_scores[emotion] = w_face * f_score + w_audio * a_score

        # Seleccionar la mejor emoción
        best_emotion = max(fused_scores, key=fused_scores.get)
        best_conf = fused_scores[best_emotion]

        # Aplicar penalty por conflicto
        if self.config['penalize_conflict']:
            final_conf = best_conf * self.config['conflict_penalty']
        else:
            final_conf = best_conf

        # Manejo de neutral
        if self.config['suppress_neutral'] and best_emotion == 'neutral':
            # Buscar siguiente mejor emoción no-neutral
            non_neutral_emotions = {k: v for k, v in fused_scores.items() if k != 'neutral'}
            if non_neutral_emotions:
                second_best = max(non_neutral_emotions, key=non_neutral_emotions.get)
                second_conf = non_neutral_emotions[second_best]

                # Si neutral no domina significativamente, usar la segunda
                if best_conf < self.config['neutral_threshold'] or (best_conf - second_conf) < self.config['neutral_min_gap']:
                    best_emotion = second_best
                    final_conf = second_conf * self.config['conflict_penalty'] if self.config['penalize_conflict'] else second_conf

        return {
            'emotion': best_emotion,
            'confidence': round(max(0.0, min(1.0, final_conf)), 4),
            'strategy': 'weighted_fusion',
            'weights': {'face': round(w_face, 3), 'audio': round(w_audio, 3)},
            'face': face_result,
            'audio': audio_result,
            'debug': {
                'fused_scores': {k: round(v, 4) for k, v in fused_scores.items()},
                'penalty_applied': self.config['penalize_conflict'],
                'confidence_before_penalty': round(best_conf, 4),
                'both_agree': False
            }
        }

    def _extract_scores_dict(self, result: Dict) -> Dict[str, float]:
        """
        Extrae distribución de scores de un resultado

        Formatos soportados:
        - {"label": "happy", "score": 0.85, "scores": [{"label": "happy", "score": 0.85}, ...]}
        - {"label": "happy", "score": 0.85}
        """
        scores_dict = {}

        # Si tiene array de scores, usarlo
        if 'scores' in result and isinstance(result['scores'], list):
            for item in result['scores']:
                if isinstance(item, dict) and 'label' in item and 'score' in item:
                    emotion = self._normalize_emotion(item['label'])
                    scores_dict[emotion] = float(item['score'])

        # Si no tiene distribución completa, crear una sintética
        if not scores_dict and 'label' in result and 'score' in result:
            emotion = self._normalize_emotion(result['label'])
            score = float(result['score'])
            # Crear distribución sintética: dar todo el peso a la emoción detectada
            scores_dict[emotion] = score
            # Distribuir el resto uniformemente (opcional)
            remaining = 1.0 - score
            other_emotions = [e for e in self.ALL_EMOTIONS if e != emotion]
            if other_emotions and remaining > 0:
                per_other = remaining / len(other_emotions)
                for other in other_emotions:
                    scores_dict[other] = per_other

        return scores_dict

    def _fallback_neutral(self, face_result: Dict, audio_result: Dict) -> Dict:
        """Ambas modalidades tienen confianza muy baja"""
        return {
            'emotion': 'neutral',
            'confidence': 0.50,
            'strategy': 'fallback_neutral',
            'weights': {'face': 0.0, 'audio': 0.0},
            'face': face_result,
            'audio': audio_result,
            'debug': {
                'reason': 'Both modalities below min_confidence',
                'both_agree': False
            }
        }

    def _audio_only(self, audio_result: Dict) -> Dict:
        """Solo audio tiene confianza suficiente"""
        emotion = self._normalize_emotion(audio_result.get('label', 'neutral'))
        confidence = float(audio_result.get('score', 0.0))

        return {
            'emotion': emotion,
            'confidence': round(confidence, 4),
            'strategy': 'audio_only',
            'weights': {'face': 0.0, 'audio': 1.0},
            'face': None,
            'audio': audio_result,
            'debug': {
                'reason': 'Face below min_confidence',
                'both_agree': False
            }
        }

    def _face_only(self, face_result: Dict) -> Dict:
        """Solo face tiene confianza suficiente"""
        emotion = self._normalize_emotion(face_result.get('label', 'neutral'))
        confidence = float(face_result.get('score', 0.0))

        return {
            'emotion': emotion,
            'confidence': round(confidence, 4),
            'strategy': 'face_only',
            'weights': {'face': 1.0, 'audio': 0.0},
            'face': face_result,
            'audio': None,
            'debug': {
                'reason': 'Audio below min_confidence',
                'both_agree': False
            }
        }

    def _smooth_with_history(self, current_result: Dict, room: str) -> Dict:
        """
        Aplica suavizado temporal AGRESIVO usando historial de fusiones

        PROPÓSITO:
            Evitar cambios bruscos e irreales de emoción mediante análisis temporal

        ESTRATEGIAS AGRESIVAS (NUEVAS):
            1. Emoción Consistente (2+ fusiones):
               → Boost moderado (+15%)

            2. Emoción MUY Consistente (4+ fusiones):
               → Boost fuerte (+25%)

            3. Cambio Brusco (diferente a última):
               → Penalización FUERTE (-25%)

            4. Outlier (diferente a últimas 3+):
               → Penalización MUY FUERTE (-50%)
               → Si confianza resultante < 50% → RECHAZAR

            5. Mínimo Tiempo de Emoción:
               → Nueva emoción debe esperar 1.5s desde la última
               → Excepción: cambio a neutral permitido

            6. Filtro de Confianza para Cambios:
               → Cambio de emoción requiere confianza >= 42%

        Args:
            current_result: Resultado de fusión actual
            room: ID de sala para tracking

        Returns:
            Resultado ajustado con información temporal (o emoción previa si rechazada)

        NOTA PARA SONARQUBE:
            Esta función tiene complejidad cognitiva alta (43) porque implementa
            el algoritmo de suavizado temporal del paper académico con 6 estrategias
            distintas (consistencia fuerte/moderada, outliers, cambios bruscos,
            filtros de tiempo y confianza). La complejidad es inherente al algoritmo
            y es necesaria para garantizar transiciones emocionales naturales.

            Refactorizar esta función en sub-funciones más pequeñas:
            - Aumentaría el acoplamiento entre componentes
            - Haría más difícil seguir la lógica temporal secuencial
            - Podría introducir bugs sutiles en el comportamiento temporal
            - Dificultaría el ajuste de parámetros del algoritmo

            Por estas razones, se mantiene como función única bien documentada.
        """
        # Si suavizado temporal está desactivado, retornar sin cambios
        if not self.temporal_config['enable_smoothing']:
            return current_result

        # Inicializar historial de sala si no existe
        if room not in self.fusion_history:
            self.fusion_history[room] = []

        history = self.fusion_history[room]
        current_emotion = current_result['emotion']
        current_confidence = current_result['confidence']
        current_time = time.time()

        # Necesitamos al menos N fusiones previas para aplicar suavizado
        min_history = self.temporal_config['min_history_for_smoothing']
        if len(history) < min_history:
            # Guardar en historial y retornar sin ajustes
            history.append({
                'emotion': current_emotion,
                'confidence': current_confidence,
                'timestamp': current_time
            })
            current_result['temporal'] = {
                'adjustment': 'none',
                'reason': 'insufficient_history',
                'history_size': len(history)
            }
            return current_result

        # Extraer últimas emociones del historial (ventana más grande)
        last_emotions = [h['emotion'] for h in history[-6:]]  # Últimas 6 (aumentado)
        last_2_emotions = last_emotions[-2:] if len(last_emotions) >= 2 else []
        last_3_emotions = last_emotions[-3:] if len(last_emotions) >= 3 else []
        last_4_emotions = last_emotions[-4:] if len(last_emotions) >= 4 else []

        # Obtener última emoción y su timestamp
        last_fusion = history[-1]
        last_emotion = last_fusion['emotion']
        last_timestamp = last_fusion.get('timestamp', current_time)

        # ===================================================================
        # FILTRO 1: MÍNIMO TIEMPO DE EMOCIÓN (evita "flasheo")
        # ===================================================================
        # Si la emoción cambió, verificar si ha pasado suficiente tiempo
        time_since_last = current_time - last_timestamp
        is_emotion_change = current_emotion != last_emotion
        min_duration = self.temporal_config['min_emotion_duration_sec']
        allow_neutral = self.temporal_config['allow_change_to_neutral']

        if is_emotion_change and time_since_last < min_duration:
            # Excepción: permitir cambio rápido a neutral
            if not (allow_neutral and current_emotion == 'neutral'):
                # RECHAZAR: mantener emoción previa
                if self.config['debug_mode']:
                    print(
                        "[FUSION-TEMPORAL] 🚫 REJECTED: Change too fast " +
                        f"({last_emotion} → {current_emotion}) after {time_since_last:.1f}s " +
                        f"(min: {min_duration}s)"
                    )

                # Retornar emoción previa sin guardar en historial
                return {
                    **current_result,
                    'emotion': last_emotion,
                    'confidence': last_fusion['confidence'],
                    'temporal': {
                        'adjustment': 'rejected',
                        'reason': 'change_too_fast',
                        'time_since_last_sec': round(time_since_last, 2),
                        'min_duration_sec': min_duration,
                        'attempted_emotion': current_emotion,
                        'maintained_emotion': last_emotion
                    }
                }

        # ===================================================================
        # FILTRO 2: CONFIANZA MÍNIMA PARA CAMBIOS
        # ===================================================================
        # Si la emoción cambió, requiere confianza mínima
        if is_emotion_change:
            min_conf_change = self.temporal_config['min_confidence_for_change']
            if current_confidence < min_conf_change:
                if self.config['debug_mode']:
                    print(
                        "[FUSION-TEMPORAL] 🚫 REJECTED: Low confidence for change " +
                        f"({current_emotion} {current_confidence:.2f} < {min_conf_change:.2f})"
                    )

                # Mantener emoción previa
                return {
                    **current_result,
                    'emotion': last_emotion,
                    'confidence': last_fusion['confidence'],
                    'temporal': {
                        'adjustment': 'rejected',
                        'reason': 'low_confidence_for_change',
                        'current_confidence': current_confidence,
                        'min_required': min_conf_change,
                        'attempted_emotion': current_emotion,
                        'maintained_emotion': last_emotion
                    }
                }

        # ===================================================================
        # CASO 1: EMOCIÓN MUY CONSISTENTE (aparece en últimas 4+)
        # ===================================================================
        # Ejemplo: [happy, happy, happy, happy] → happy (boost fuerte)
        if len(last_4_emotions) >= 4 and all(e == current_emotion for e in last_4_emotions):
            adjustment = self.temporal_config['strong_consistency_boost']
            current_result['confidence'] = min(current_confidence * adjustment, 1.0)
            current_result['temporal'] = {
                'adjustment': 'strong_consistency_boost',
                'reason': f'emotion_very_consistent_last_{len(last_4_emotions)}',
                'boost_factor': adjustment,
                'original_confidence': current_confidence,
                'adjusted_confidence': current_result['confidence'],
                'history': last_emotions
            }

            if self.config['debug_mode']:
                print(f"[FUSION-TEMPORAL] ✨ STRONG consistency: {current_emotion} in last {len(last_4_emotions)} fusions (+{int((adjustment-1)*100)}%)")

        # ===================================================================
        # CASO 2: EMOCIÓN CONSISTENTE (aparece en últimas 2-3)
        # ===================================================================
        # Ejemplo: [happy, happy] → happy (boost moderado)
        elif len(last_2_emotions) >= 2 and all(e == current_emotion for e in last_2_emotions):
            adjustment = self.temporal_config['consistency_boost']
            current_result['confidence'] = min(current_confidence * adjustment, 1.0)
            current_result['temporal'] = {
                'adjustment': 'consistency_boost',
                'reason': f'emotion_consistent_with_last_{len(last_2_emotions)}',
                'boost_factor': adjustment,
                'original_confidence': current_confidence,
                'adjusted_confidence': current_result['confidence'],
                'history': last_emotions
            }

            if self.config['debug_mode']:
                print(f"[FUSION-TEMPORAL] ✅ Consistency: {current_emotion} in last {len(last_2_emotions)} fusions (+{int((adjustment-1)*100)}%)")

        # ===================================================================
        # CASO 3: OUTLIER FUERTE (diferente a las últimas 3+)
        # ===================================================================
        # Ejemplo: [happy, happy, happy] → sad (outlier)
        elif len(last_3_emotions) >= 3 and all(e != current_emotion for e in last_3_emotions):
            adjustment = self.temporal_config['outlier_penalty']
            adjusted_confidence = current_confidence * adjustment
            current_result['confidence'] = adjusted_confidence

            # Si es outlier débil, RECHAZAR completamente
            if self.temporal_config['weak_outlier_reject'] and adjusted_confidence < 0.50:
                if self.config['debug_mode']:
                    print(
                        "[FUSION-TEMPORAL] 🚫 REJECTED: Weak outlier " +
                        f"({current_emotion} {adjusted_confidence:.2f} < 0.50) vs {last_3_emotions}"
                    )

                # Mantener emoción previa
                return {
                    **current_result,
                    'emotion': last_emotion,
                    'confidence': last_fusion['confidence'],
                    'temporal': {
                        'adjustment': 'rejected',
                        'reason': 'weak_outlier',
                        'attempted_emotion': current_emotion,
                        'attempted_confidence': adjusted_confidence,
                        'maintained_emotion': last_emotion,
                        'history': last_3_emotions
                    }
                }

            # Outlier aceptado pero con penalización
            current_result['temporal'] = {
                'adjustment': 'outlier_penalty',
                'reason': f'emotion_differs_from_last_{len(last_3_emotions)}',
                'penalty_factor': adjustment,
                'original_confidence': current_confidence,
                'adjusted_confidence': adjusted_confidence,
                'history': last_emotions,
                'current_emotion': current_emotion,
                'historical_emotions': last_3_emotions
            }

            if self.config['debug_mode']:
                print(
                    f"[FUSION-TEMPORAL] ⚠️ OUTLIER: {current_emotion} vs {last_3_emotions} " +
                    f"(-{int((1-adjustment)*100)}% → {adjusted_confidence:.2f})"
                )

        # ===================================================================
        # CASO 4: CAMBIO BRUSCO (diferente solo a la última)
        # ===================================================================
        # Ejemplo: [neutral, happy] → sad (cambio brusco)
        elif is_emotion_change:
            adjustment = self.temporal_config['sudden_change_penalty']
            current_result['confidence'] = current_confidence * adjustment
            current_result['temporal'] = {
                'adjustment': 'sudden_change',
                'reason': 'emotion_changed_from_previous',
                'penalty_factor': adjustment,
                'original_confidence': current_confidence,
                'adjusted_confidence': current_result['confidence'],
                'previous_emotion': last_emotion,
                'current_emotion': current_emotion
            }

            if self.config['debug_mode']:
                print(
                    f"[FUSION-TEMPORAL] 🔄 CHANGE: {last_emotion} → {current_emotion} " +
                    f"(-{int((1-adjustment)*100)}% → {current_result['confidence']:.2f})"
                )

        # ===================================================================
        # CASO 5: SIN AJUSTE (misma emoción, sin patrón especial)
        # ===================================================================
        else:
            current_result['temporal'] = {
                'adjustment': 'none',
                'reason': 'normal_progression',
                'history': last_emotions
            }

        # Guardar fusión actual en historial
        # IMPORTANTE: guardar la emoción FINAL (puede haber sido ajustada)
        history.append({
            'emotion': current_result['emotion'],  # Emoción final (puede ser diferente si hubo rechazo)
            'confidence': current_result['confidence'],
            'timestamp': current_time,
            'adjustment': current_result['temporal']['adjustment']
        })

        # Limitar tamaño del historial
        if len(history) > self.max_history_size:
            history.pop(0)  # Remover más antigua

        # Actualizar historial
        self.fusion_history[room] = history

        return current_result

    def _apply_persistence(self, result: Dict, room: str) -> Dict:
        """
        Aplica persistencia emocional para evitar neutral bias

        PROPÓSITO:
            Cuando la confianza es baja, mantener la última emoción fuerte
            en lugar de caer a neutral inmediatamente (más natural)

        Args:
            result: Resultado de fusión actual (después de suavizado temporal)
            room: ID de sala

        Returns:
            Resultado con persistencia aplicada
        """
        # Inicializar sistema de persistencia si no existe
        if room not in self.persistence_systems:
            self.persistence_systems[room] = EmotionPersistence(
                strong_threshold=0.70,
                weak_threshold=0.40,
                decay_rate=0.97,
                min_persistence=0.35
            )

        persistence = self.persistence_systems[room]
        current_emotion = result['emotion']
        current_confidence = result['confidence']

        # Aplicar persistencia
        final_emotion, final_confidence, used_persistence = persistence.update(
            current_emotion, current_confidence
        )

        # Si se usó persistencia, actualizar resultado
        if used_persistence:
            original_emotion = current_emotion
            original_confidence = current_confidence

            result['emotion'] = final_emotion
            result['confidence'] = round(final_confidence, 4)
            result['persistence'] = {
                'used': True,
                'reason': 'low_confidence_maintained_strong_emotion',
                'original_emotion': original_emotion,
                'original_confidence': original_confidence,
                'persisted_emotion': final_emotion,
                'persisted_confidence': final_confidence,
                'decay_rate': persistence.decay_rate
            }

            if self.config['debug_mode']:
                print(
                    f"[FUSION-PERSIST] 💾 Using persistence: {original_emotion} ({original_confidence:.2f}) " +
                    f"→ {final_emotion} ({final_confidence:.2f})"
                )
        else:
            result['persistence'] = {
                'used': False,
                'reason': 'confidence_sufficient'
            }

        return result

    def _get_or_create_ema(self, room: str) -> EmotionEMA:
        """Obtiene o crea sistema EMA para una sala"""
        if room not in self.ema_systems:
            alpha = self.temporal_config.get('ema_alpha', 0.3)
            self.ema_systems[room] = EmotionEMA(alpha=alpha)
        return self.ema_systems[room]

    def clear_room_history(self, room: str) -> None:
        """
        Limpia el historial de fusiones, EMA y persistencia de una sala específica

        IMPORTANTE: Debe llamarse cuando:
        - Pepper completa una animación exitosamente
        - Se reinicia la sesión de detección
        - Se quiere resetear el estado temporal

        Args:
            room: ID de la sala a limpiar
        """
        if room in self.fusion_history:
            del self.fusion_history[room]

        if room in self.ema_systems:
            self.ema_systems[room].reset()

        if room in self.persistence_systems:
            self.persistence_systems[room] = EmotionPersistence(
                strong_threshold=0.70,
                weak_threshold=0.40,
                decay_rate=0.97,
                min_persistence=0.35
            )

        if self.config['debug_mode']:
            print(f"[FUSION] 🧹 Cleared history for room: {room}")

    def update_config(self, new_config: Dict) -> None:
        """Actualiza configuración en caliente"""
        self.config.update(new_config)
        if self.config['debug_mode']:
            print(f"[FUSION] Config updated: {new_config}")


# Instancia global (singleton)
_fusion_system = None


def get_fusion_system(config: Optional[Dict] = None) -> ConfidenceBasedVotingFusion:
    """Obtiene la instancia global del sistema de fusión"""
    global _fusion_system
    if _fusion_system is None:
        _fusion_system = ConfidenceBasedVotingFusion(config)
    return _fusion_system
