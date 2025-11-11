# app/state.py
"""
Global state management for Pepper process status
"""
from __future__ import annotations
import threading
from typing import Dict, Any
import logging

logger = logging.getLogger("state")

class PepperState:
    """Thread-safe state manager for Pepper process status"""

    def __init__(self):
        self._lock = threading.RLock()
        self._state: Dict[str, Any] = {
            "proce": 1,  # 1 = Pepper available, 0 = Pepper busy
            "last_emotion": None,
            "last_update": None,
            "room": None
        }

    def get_proce(self, room: str = None) -> int:
        """Get Pepper process status

        Returns:
            1 if Pepper is available to receive scripts
            0 if Pepper is busy executing a script
        """
        with self._lock:
            return self._state["proce"]

    def set_proce(self, value: int, room: str = None) -> bool:
        """Set Pepper process status

        Args:
            value: 1 for available, 0 for busy
            room: Optional room identifier

        Returns:
            True if state was changed successfully
        """
        if value not in (0, 1):
            logger.warning(f"Invalid proce value: {value}. Must be 0 or 1")
            return False

        with self._lock:
            old_value = self._state["proce"]
            self._state["proce"] = value
            self._state["room"] = room

            if old_value != value:
                status = "BUSY" if value == 0 else "AVAILABLE"
                logger.info(f"Pepper status changed: {status} (room: {room})")

            return True

    def is_pepper_available(self, room: str = None) -> bool:
        """Check if Pepper is available to receive new scripts"""
        return self.get_proce(room) == 1

    def is_pepper_busy(self, room: str = None) -> bool:
        """Check if Pepper is currently executing a script"""
        return self.get_proce(room) == 0

    def set_busy(self, emotion: str = None, room: str = None) -> bool:
        """Mark Pepper as busy with optional emotion context"""
        with self._lock:
            self._state["last_emotion"] = emotion
            return self.set_proce(0, room)

    def set_available(self, room: str = None) -> bool:
        """Mark Pepper as available"""
        return self.set_proce(1, room)

    def get_full_state(self) -> Dict[str, Any]:
        """Get complete state for debugging"""
        with self._lock:
            return self._state.copy()

# Global singleton instance
_pepper_state = PepperState()

def get_pepper_state() -> PepperState:
    """Get the global Pepper state instance"""
    return _pepper_state


# ===== EMOTION BUFFER =====

class EmotionBuffer:
    """
    Buffer temporal para almacenar detecciones de face y audio por room
    Permite realizar fusión cuando ambas modalidades están disponibles

    SINCRONIZACIÓN VÍA PEPPER STATE:
    - Sensores solo detectan cuando proce=1 (Pepper disponible)
    - Cuando llega audio → proce=0 → fusión inmediata → enviar a Pepper
    - Pepper termina animación → proce=1 → sensores reactivan

    MEJORAS DE TIMEOUT:
    - Limpieza automática de datos antiguos (> MAX_AGE_SECONDS)
    - Fusión parcial si una modalidad no llega en FUSION_TIMEOUT
    - Fallback a modalidad única si timeout excedido
    - Logs detallados de timeouts para debugging
    """

    def __init__(self, max_size: int = 5, timeout: float = 10.0, max_age: float = 15.0, fusion_timeout: float = 10.0):
        """
        Args:
            max_size: Número máximo de detecciones por modalidad/room
            timeout: Timeout en segundos para considerar una detección válida
            max_age: Edad máxima de datos antes de ser descartados (limpieza automática)
            fusion_timeout: Tiempo máximo de espera para fusión completa antes de usar fallback
        """
        self._lock = threading.RLock()
        self.max_size = max_size
        self.timeout = timeout
        self.max_age = max_age
        self.fusion_timeout = fusion_timeout
        # Estructura: {room: {"face": [...], "audio": [...]}}
        self._buffer: Dict[str, Dict[str, list]] = {}
        # WebSocket event callbacks
        self._event_callbacks = []
        # Estadísticas de timeouts
        self._timeout_stats: Dict[str, Dict[str, int]] = {}  # {room: {face_timeouts, audio_timeouts, partial_fusions}}

    def add_face(self, room: str, result: Dict[str, Any]) -> None:
        """
        Agrega detección facial al buffer (sin emitir evento)

        Face se acumula en el buffer esperando que llegue audio.
        NO emite eventos WebSocket - la fusión se triggerea desde add_audio.

        Ahora soporta resultados agregados de múltiples frames.
        """
        with self._lock:
            if room not in self._buffer:
                self._buffer[room] = {"face": [], "audio": []}

            # Agregar timestamp
            result["timestamp"] = self._get_timestamp()

            self._buffer[room]["face"].append(result)

            # Mantener solo las últimas N detecciones
            if len(self._buffer[room]["face"]) > self.max_size:
                self._buffer[room]["face"].pop(0)

            # Log con información de agregación si está disponible
            frame_count = result.get('frameCount', 0)
            consensus = result.get('consensusRatio', 0)

            if frame_count > 0:
                logger.debug(
                    f"[BUFFER] 👤 Face window buffered: {result.get('label')} "
                    f"({result.get('score', 0):.2f}) | "
                    f"{frame_count} frames | consensus: {consensus:.1%}"
                )
            else:
                logger.debug(
                    f"[BUFFER] 👤 Face buffered: {result.get('label')} "
                    f"({result.get('score', 0):.2f})"
                )

    def add_audio(self, room: str, result: Dict[str, Any]) -> None:
        """
        Agrega detección de audio al buffer y triggerea fusión inmediata

        FLUJO:
        1. Guardar audio en buffer
        2. Emitir evento de audio al WebSocket
        3. Si hay face disponible → emitir evento de fusión inmediatamente

        Esto garantiza que cuando llega audio, la fusión ocurre sin esperar
        a que llegue otro sensor.
        """
        with self._lock:
            if room not in self._buffer:
                self._buffer[room] = {"face": [], "audio": []}

            # Agregar timestamp
            result["timestamp"] = self._get_timestamp()

            self._buffer[room]["audio"].append(result)

            # Mantener solo las últimas N detecciones
            if len(self._buffer[room]["audio"]) > self.max_size:
                self._buffer[room]["audio"].pop(0)

            logger.info(
                f"[BUFFER] 🎤 Audio arrived: {result.get('label')} ({result.get('score', 0):.2f}) "
                "- triggering fusion"
            )

            # Emitir audio primero
            self._emit_event("detection", room, "audio", result)

            # Si hay face disponible, emitir face también para triggerar fusión
            face_result = self.get_latest_face(room)
            if face_result:
                logger.info(
                    f"[BUFFER] 👤 Using buffered face: {face_result.get('label')} "
                    f"({face_result.get('score', 0):.2f})"
                )
                self._emit_event("detection", room, "face", face_result)

    def get_latest_face(self, room: str) -> Dict[str, Any] | None:
        """Obtiene la última detección facial válida (no expirada)"""
        with self._lock:
            if room not in self._buffer or not self._buffer[room]["face"]:
                return None

            # Limpiar detectiones expiradas
            self._clean_expired(room, "face")

            if self._buffer[room]["face"]:
                return self._buffer[room]["face"][-1]

            return None

    def get_latest_audio(self, room: str) -> Dict[str, Any] | None:
        """Obtiene la última detección de audio válida (no expirada)"""
        with self._lock:
            if room not in self._buffer or not self._buffer[room]["audio"]:
                return None

            # Limpiar detecciones expiradas
            self._clean_expired(room, "audio")

            if self._buffer[room]["audio"]:
                return self._buffer[room]["audio"][-1]

            return None

    def has_both(self, room: str) -> bool:
        """
        Verifica si hay detecciones válidas de ambas modalidades
        """
        face = self.get_latest_face(room)
        audio = self.get_latest_audio(room)
        return face is not None and audio is not None

    def clear_room(self, room: str) -> None:
        """Limpia buffer de una room específica"""
        with self._lock:
            if room in self._buffer:
                del self._buffer[room]
                logger.debug(f"[BUFFER] Cleared buffer for room {room}")

    def clear_all(self) -> None:
        """Limpia todo el buffer"""
        with self._lock:
            self._buffer.clear()
            logger.debug("[BUFFER] Cleared all buffers")

    def _clean_expired(self, room: str, modality: str) -> int:
        """
        Elimina detecciones expiradas de una modalidad

        Returns:
            Número de detecciones eliminadas
        """
        if room not in self._buffer:
            return 0

        now = self._get_timestamp()
        initial_count = len(self._buffer[room][modality])

        self._buffer[room][modality] = [
            det for det in self._buffer[room][modality]
            if (now - det.get("timestamp", 0)) <= self.timeout
        ]

        removed = initial_count - len(self._buffer[room][modality])

        if removed > 0:
            logger.debug(f"[BUFFER] Cleaned {removed} expired {modality} detections from room {room}")

        return removed

    def clean_old_data(self, room: str = None) -> Dict[str, int]:
        """
        Limpia datos muy antiguos (> max_age) de todas las rooms o una específica

        Args:
            room: Room específica o None para todas

        Returns:
            Dict con estadísticas de limpieza
        """
        with self._lock:
            stats = {"face_removed": 0, "audio_removed": 0, "rooms_cleaned": 0}
            now = self._get_timestamp()

            rooms_to_clean = [room] if room else list(self._buffer.keys())

            for r in rooms_to_clean:
                if r not in self._buffer:
                    continue

                # Limpiar face antiguos
                initial_face = len(self._buffer[r]["face"])
                self._buffer[r]["face"] = [
                    det for det in self._buffer[r]["face"]
                    if (now - det.get("timestamp", 0)) <= self.max_age
                ]
                face_removed = initial_face - len(self._buffer[r]["face"])
                stats["face_removed"] += face_removed

                # Limpiar audio antiguos
                initial_audio = len(self._buffer[r]["audio"])
                self._buffer[r]["audio"] = [
                    det for det in self._buffer[r]["audio"]
                    if (now - det.get("timestamp", 0)) <= self.max_age
                ]
                audio_removed = initial_audio - len(self._buffer[r]["audio"])
                stats["audio_removed"] += audio_removed

                if face_removed > 0 or audio_removed > 0:
                    stats["rooms_cleaned"] += 1
                    logger.info(
                        f"[BUFFER] Auto-cleanup room {r}: "
                        f"removed {face_removed} face, {audio_removed} audio (older than {self.max_age}s)"
                    )

            return stats

    def check_fusion_timeout(self, room: str) -> Dict[str, Any]:
        """
        Verifica si hay timeout de fusión y determina estrategia de fallback

        Returns:
            {
                "should_fuse": bool,
                "strategy": "both" | "face_only" | "audio_only" | "none",
                "reason": str,
                "face_age": float | None,
                "audio_age": float | None
            }
        """
        with self._lock:
            if room not in self._buffer:
                return {
                    "should_fuse": False,
                    "strategy": "none",
                    "reason": "room_not_initialized",
                    "face_age": None,
                    "audio_age": None
                }

            now = self._get_timestamp()

            # Obtener edades de las últimas detecciones
            face_age = None
            audio_age = None

            if self._buffer[room]["face"]:
                last_face_ts = self._buffer[room]["face"][-1].get("timestamp", 0)
                face_age = now - last_face_ts

            if self._buffer[room]["audio"]:
                last_audio_ts = self._buffer[room]["audio"][-1].get("timestamp", 0)
                audio_age = now - last_audio_ts

            # Caso 1: Ambas modalidades disponibles y frescas
            if face_age is not None and audio_age is not None:
                if face_age <= self.fusion_timeout and audio_age <= self.fusion_timeout:
                    return {
                        "should_fuse": True,
                        "strategy": "both",
                        "reason": "both_fresh",
                        "face_age": round(face_age, 2),
                        "audio_age": round(audio_age, 2)
                    }

            # Caso 2: Solo face disponible
            if face_age is not None and face_age <= self.fusion_timeout:
                if audio_age is None or audio_age > self.fusion_timeout:
                    self._increment_timeout_stat(room, "audio_timeouts")
                    return {
                        "should_fuse": True,
                        "strategy": "face_only",
                        "reason": "audio_timeout",
                        "face_age": round(face_age, 2),
                        "audio_age": round(audio_age, 2) if audio_age else None
                    }

            # Caso 3: Solo audio disponible
            if audio_age is not None and audio_age <= self.fusion_timeout:
                if face_age is None or face_age > self.fusion_timeout:
                    self._increment_timeout_stat(room, "face_timeouts")
                    return {
                        "should_fuse": True,
                        "strategy": "audio_only",
                        "reason": "face_timeout",
                        "face_age": round(face_age, 2) if face_age else None,
                        "audio_age": round(audio_age, 2)
                    }

            # Caso 4: Ambas expiradas o no disponibles
            return {
                "should_fuse": False,
                "strategy": "none",
                "reason": "both_timeout_or_missing",
                "face_age": round(face_age, 2) if face_age else None,
                "audio_age": round(audio_age, 2) if audio_age else None
            }

    def _increment_timeout_stat(self, room: str, stat_key: str) -> None:
        """Incrementa contador de estadísticas de timeout"""
        if room not in self._timeout_stats:
            self._timeout_stats[room] = {
                "face_timeouts": 0,
                "audio_timeouts": 0,
                "partial_fusions": 0
            }
        self._timeout_stats[room][stat_key] = self._timeout_stats[room].get(stat_key, 0) + 1

    def _get_timestamp(self) -> float:
        """Obtiene timestamp actual"""
        import time
        return time.time()

    def get_stats(self, room: str = None) -> Dict[str, Any]:
        """Obtiene estadísticas del buffer con información de frescura de datos y timeouts"""
        with self._lock:
            if room:
                if room in self._buffer:
                    now = self._get_timestamp()

                    # Calcular edad de última detección de cada modalidad
                    face_latest_age_ms = None
                    audio_latest_age_ms = None

                    if self._buffer[room]["face"]:
                        last_face_ts = self._buffer[room]["face"][-1].get("timestamp", 0)
                        face_latest_age_ms = int((now - last_face_ts) * 1000)

                    if self._buffer[room]["audio"]:
                        last_audio_ts = self._buffer[room]["audio"][-1].get("timestamp", 0)
                        audio_latest_age_ms = int((now - last_audio_ts) * 1000)

                    # Obtener estadísticas de timeout
                    timeout_stats = self._timeout_stats.get(room, {
                        "face_timeouts": 0,
                        "audio_timeouts": 0,
                        "partial_fusions": 0
                    })

                    return {
                        "room": room,
                        "face_count": len(self._buffer[room]["face"]),
                        "audio_count": len(self._buffer[room]["audio"]),
                        "has_both": self.has_both(room),
                        "face_latest_age_ms": face_latest_age_ms,
                        "audio_latest_age_ms": audio_latest_age_ms,
                        "timeout_threshold_ms": int(self.fusion_timeout * 1000),
                        "max_age_ms": int(self.max_age * 1000),
                        "timeout_stats": timeout_stats
                    }
                return {
                    "room": room,
                    "face_count": 0,
                    "audio_count": 0,
                    "has_both": False,
                    "face_latest_age_ms": None,
                    "audio_latest_age_ms": None,
                    "timeout_threshold_ms": int(self.fusion_timeout * 1000),
                    "max_age_ms": int(self.max_age * 1000),
                    "timeout_stats": {"face_timeouts": 0, "audio_timeouts": 0, "partial_fusions": 0}
                }
            else:
                # Estadísticas globales
                total_timeouts = {
                    "face_timeouts": 0,
                    "audio_timeouts": 0,
                    "partial_fusions": 0
                }
                for stats in self._timeout_stats.values():
                    total_timeouts["face_timeouts"] += stats.get("face_timeouts", 0)
                    total_timeouts["audio_timeouts"] += stats.get("audio_timeouts", 0)
                    total_timeouts["partial_fusions"] += stats.get("partial_fusions", 0)

                return {
                    "total_rooms": len(self._buffer),
                    "rooms": list(self._buffer.keys()),
                    "global_timeout_stats": total_timeouts
                }

    def register_event_callback(self, callback):
        """
        Registra un callback para eventos del buffer

        Args:
            callback: Función async que recibe (event_type, room, modality, data)
        """
        self._event_callbacks.append(callback)
        logger.debug(f"[BUFFER] Registered event callback. Total callbacks: {len(self._event_callbacks)}")

    def _emit_event(self, event_type: str, room: str, modality: str, data: Dict[str, Any]):
        """
        Emite un evento a todos los callbacks registrados

        Args:
            event_type: Tipo de evento ("detection", "fusion")
            room: Room ID
            modality: "face" o "audio"
            data: Datos del evento
        """
        import asyncio

        for callback in self._event_callbacks:
            try:
                # Ejecutar callback async en el event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(callback(event_type, room, modality, data))
                else:
                    # Si no hay loop corriendo, skip
                    logger.warning("[BUFFER] No event loop running, skipping callback")
            except Exception as e:
                logger.error(f"[BUFFER] Error in event callback: {e}")


# Global singleton instance
_emotion_buffer = EmotionBuffer()

def get_emotion_buffer() -> EmotionBuffer:
    """Get the global EmotionBuffer instance"""
    return _emotion_buffer