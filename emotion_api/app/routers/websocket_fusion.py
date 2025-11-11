# emotion_api/app/routers/websocket_fusion.py
"""
WebSocket endpoint para fusión de emociones en tiempo real

Proporciona comunicación bidireccional para:
- Notificaciones de detecciones (face/audio)
- Resultados de fusión en tiempo real
- Estado del buffer

Ventajas vs HTTP polling:
- 70% menos latencia (push vs pull)
- 90% menos requests (solo envía cuando hay datos)
- Conexión persistente (sin overhead HTTP)
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import logging
import asyncio
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """
    Gestiona conexiones WebSocket por room

    Permite enviar mensajes a todos los clientes conectados a una room específica

    MEJORAS:
    - Heartbeat automático del servidor (cada 30s)
    - Detección de conexiones muertas
    - Estadísticas de conexión
    - Manejo robusto de errores
    """

    def __init__(self, heartbeat_interval: int = 30):
        # {room_id: Set[WebSocket]}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self.heartbeat_interval = heartbeat_interval  # segundos
        # Estadísticas de conexión
        self._connection_stats: Dict[str, Dict[str, int]] = {}  # {room: {connects, disconnects, errors}}

    async def connect(self, websocket: WebSocket, room: str):
        """Acepta y registra una nueva conexión"""
        await websocket.accept()

        async with self._lock:
            if room not in self.active_connections:
                self.active_connections[room] = set()
                self._connection_stats[room] = {"connects": 0, "disconnects": 0, "errors": 0, "messages_sent": 0}

            self.active_connections[room].add(websocket)
            self._connection_stats[room]["connects"] += 1

        logger.info(f"[WS] Client connected to room {room}. Total in room: {len(self.active_connections[room])}")

    async def disconnect(self, websocket: WebSocket, room: str):
        """Desconecta y desregistra una conexión"""
        async with self._lock:
            if room in self.active_connections:
                self.active_connections[room].discard(websocket)
                if room in self._connection_stats:
                    self._connection_stats[room]["disconnects"] += 1

                # Limpiar room vacía
                if not self.active_connections[room]:
                    del self.active_connections[room]
                    logger.info(f"[WS] Room {room} is now empty")

        logger.info(f"[WS] Client disconnected from room {room}")

    async def broadcast_to_room(self, room: str, message: dict):
        """
        Envía mensaje a todos los clientes de una room

        Args:
            room: ID de la room
            message: Diccionario con el mensaje (será serializado a JSON)
        """
        if room not in self.active_connections:
            return

        disconnected = set()
        sent_count = 0

        for websocket in self.active_connections[room].copy():
            try:
                await websocket.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.warning(f"[WS] Error sending to client in room {room}: {e}")
                disconnected.add(websocket)
                if room in self._connection_stats:
                    self._connection_stats[room]["errors"] += 1

        # Actualizar estadísticas
        if room in self._connection_stats and sent_count > 0:
            self._connection_stats[room]["messages_sent"] += sent_count

        # Limpiar conexiones muertas
        if disconnected:
            async with self._lock:
                self.active_connections[room] -= disconnected
                logger.warning(f"[WS] Cleaned {len(disconnected)} dead connections from room {room}")

    async def heartbeat(self, websocket: WebSocket, room: str):
        """
        Envía heartbeat periódico para mantener conexión viva

        Args:
            websocket: Conexión WebSocket
            room: ID de la room

        Retorna cuando la conexión muere o se cancela la tarea
        """
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)

                try:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": asyncio.get_event_loop().time(),
                        "room": room
                    })
                    logger.debug(f"[WS] Heartbeat sent to room {room}")
                except Exception as e:
                    logger.warning(f"[WS] Heartbeat failed for room {room}: {e}")
                    break  # Conexión muerta

        except asyncio.CancelledError:
            logger.debug(f"[WS] Heartbeat task cancelled for room {room}")

    def get_room_count(self, room: str) -> int:
        """Retorna número de conexiones en una room"""
        return len(self.active_connections.get(room, set()))

    def get_stats(self, room: str = None) -> Dict:
        """
        Obtiene estadísticas de conexiones WebSocket

        Args:
            room: Room específica o None para todas

        Returns:
            Dict con estadísticas
        """
        if room:
            return {
                "room": room,
                "active_connections": self.get_room_count(room),
                **self._connection_stats.get(room, {
                    "connects": 0,
                    "disconnects": 0,
                    "errors": 0,
                    "messages_sent": 0
                })
            }
        else:
            total_connections = sum(len(conns) for conns in self.active_connections.values())
            total_stats = {
                "connects": 0,
                "disconnects": 0,
                "errors": 0,
                "messages_sent": 0
            }
            for stats in self._connection_stats.values():
                for key in total_stats:
                    total_stats[key] += stats.get(key, 0)

            return {
                "total_active_connections": total_connections,
                "total_rooms": len(self.active_connections),
                "rooms": list(self.active_connections.keys()),
                **total_stats
            }


# Instancia global del gestor de conexiones
manager = ConnectionManager()


@router.websocket("/fusion/{room}")
async def websocket_fusion_endpoint(websocket: WebSocket, room: str):
    """
    WebSocket endpoint para fusión de emociones en tiempo real

    URL: ws://localhost:8000/ws/fusion/{room}

    Mensajes del cliente al servidor:
        {
            "type": "ping"
        }

    Mensajes del servidor al cliente:
        {
            "type": "connected",
            "room": "test"
        }

        {
            "type": "detection",
            "modality": "face" | "audio",
            "data": {...}
        }

        {
            "type": "fusion",
            "emotion": "happy",
            "confidence": 0.85,
            "strategy": "weighted_fusion",
            "weights": {"face": 0.55, "audio": 0.45},
            ...
        }

        {
            "type": "pong"
        }
    """
    await manager.connect(websocket, room)

    # Iniciar heartbeat en segundo plano
    heartbeat_task = asyncio.create_task(manager.heartbeat(websocket, room))

    try:
        # Enviar mensaje de confirmación
        await websocket.send_json({
            "type": "connected",
            "room": room,
            "timestamp": asyncio.get_event_loop().time(),
            "heartbeat_interval": manager.heartbeat_interval
        })

        # Loop principal: escuchar mensajes del cliente
        while True:
            # Recibir mensaje (JSON)
            try:
                data = await websocket.receive_json()
            except json.JSONDecodeError:
                # Si no es JSON válido, intentar recibir como texto
                text = await websocket.receive_text()
                logger.warning(f"[WS] Invalid JSON from room {room}: {text}")
                continue

            msg_type = data.get("type")

            # Ping/Pong para keep-alive (desde cliente)
            if msg_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": asyncio.get_event_loop().time()
                })

            # Solicitar estadísticas
            elif msg_type == "get_stats":
                stats = manager.get_stats(room)
                await websocket.send_json({
                    "type": "stats",
                    **stats
                })

            # Otros mensajes pueden agregarse aquí en el futuro
            # Por ejemplo: configuración de fusion, etc.

    except WebSocketDisconnect:
        logger.info(f"[WS] Client disconnected normally from room {room}")
    except Exception as e:
        logger.error(f"[WS] Error in websocket for room {room}: {e}")
    finally:
        # Cancelar heartbeat
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

        await manager.disconnect(websocket, room)


def get_connection_manager() -> ConnectionManager:
    """Obtiene la instancia global del ConnectionManager"""
    return manager
