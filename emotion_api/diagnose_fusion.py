"""
Script de diagnostico para sistema de fusion emocional

PROPOSITO:
    Diagnosticar y solucionar problemas cuando el sistema de fusion
    se "atasca" en una emocion (ej: siempre retorna "surprised")

USO:
    python diagnose_fusion.py [room_id]

ACCIONES:
    1. Muestra el historial de fusiones de la room
    2. Muestra el estado de persistencia emocional
    3. Muestra la configuracion de suavizado temporal
    4. OPCIONES para solucionar:
       a) Limpiar historial de fusion
       b) Deshabilitar suavizado temporal temporalmente
       c) Ajustar parametros de filtros
"""

import requests
import json
import sys
import io

# Fix para Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configuración
EMOTION_API_BASE = "http://localhost:8000"
DEFAULT_ROOM = "default"


def print_header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def get_fusion_history(room):
    """Obtiene el historial de fusiones de una room"""
    try:
        response = requests.get(f"{EMOTION_API_BASE}/fusion/history/{room}")
        if response.ok:
            return response.json()
        else:
            print(f"❌ Error obteniendo historial: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error conectando al servidor: {e}")
        return None


def get_temporal_config():
    """Obtiene configuración de suavizado temporal"""
    try:
        response = requests.get(f"{EMOTION_API_BASE}/fusion/temporal-config")
        if response.ok:
            return response.json()
        else:
            print(f"❌ Error obteniendo config temporal: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_buffer_stats(room):
    """Obtiene estadísticas del buffer"""
    try:
        response = requests.get(f"{EMOTION_API_BASE}/fusion/buffer-stats", params={"room": room})
        if response.ok:
            return response.json()
        else:
            return None
    except Exception:
        return None


def clear_buffer(room):
    """Limpia el buffer y historial de fusión"""
    try:
        data = {"room": room} if room else {}
        response = requests.post(
            f"{EMOTION_API_BASE}/fusion/clear-buffer",
            data=data
        )
        if response.ok:
            result = response.json()
            print(f"\n✅ {result.get('message', 'Buffer cleared')}")
            return True
        else:
            print(f"\n❌ Error limpiando buffer: {response.status_code}")
            return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def disable_temporal_smoothing():
    """Deshabilita temporalmente el suavizado temporal"""
    try:
        config = {
            "enable_smoothing": False,
            "enable_persistence": False
        }
        response = requests.post(
            f"{EMOTION_API_BASE}/fusion/temporal-config",
            json=config
        )
        if response.ok:
            print("\n✅ Suavizado temporal DESHABILITADO")
            print("   - enable_smoothing = False")
            print("   - enable_persistence = False")
            print("\n   ⚠️ RECUERDA re-habilitar después para mejor UX")
            return True
        else:
            print(f"\n❌ Error actualizando config: {response.status_code}")
            return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def make_filters_less_aggressive():
    """Hace los filtros temporales menos agresivos"""
    try:
        config = {
            "min_emotion_duration_sec": 0.5,      # Reducir de 1.5s a 0.5s
            "min_confidence_for_change": 0.30,    # Reducir de 0.42 a 0.30
            "sudden_change_penalty": 0.90,        # Menos penalty: -10% (antes -25%)
            "outlier_penalty": 0.75,              # Menos penalty: -25% (antes -50%)
            "weak_outlier_reject": False,         # No rechazar outliers débiles
        }
        response = requests.post(
            f"{EMOTION_API_BASE}/fusion/temporal-config",
            json=config
        )
        if response.ok:
            print("\n✅ Filtros temporales SUAVIZADOS")
            print("   - min_emotion_duration_sec: 1.5s → 0.5s")
            print("   - min_confidence_for_change: 0.42 → 0.30")
            print("   - sudden_change_penalty: 0.75 → 0.90 (-25% → -10%)")
            print("   - outlier_penalty: 0.50 → 0.75 (-50% → -25%)")
            print("   - weak_outlier_reject: True → False")
            return True
        else:
            print(f"\n❌ Error actualizando config: {response.status_code}")
            return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def diagnose(room):
    """Ejecuta diagnóstico completo"""

    print_header(f"DIAGNÓSTICO DE FUSIÓN EMOCIONAL - Room: {room}")

    # 1. Historial de fusiones
    print("\n📊 HISTORIAL DE FUSIONES:")
    print("-" * 80)
    history_data = get_fusion_history(room)

    if history_data:
        history = history_data.get("history", [])

        if not history:
            print("   ✅ Historial VACÍO (normal al inicio)")
        else:
            print(f"   Total de fusiones en historial: {len(history)}")
            print(f"\n   Últimas 10 fusiones:")
            for i, fusion in enumerate(history[-10:], 1):
                emotion = fusion.get("emotion", "?")
                confidence = fusion.get("confidence", 0)
                adjustment = fusion.get("adjustment", "none")
                print(f"      {i}. {emotion:12s} ({confidence:.2f}) [{adjustment}]")

            # Análisis de consistencia
            emotions_in_history = [f.get("emotion") for f in history]
            emotion_counts = {}
            for e in emotions_in_history:
                emotion_counts[e] = emotion_counts.get(e, 0) + 1

            print(f"\n   📈 Distribución de emociones:")
            for emotion, count in sorted(emotion_counts.items(), key=lambda x: -x[1]):
                percentage = (count / len(history)) * 100
                bar = "█" * int(percentage / 2)
                print(f"      {emotion:12s}: {bar} {percentage:5.1f}% ({count}/{len(history)})")

            # Detectar si está atascado
            last_5 = emotions_in_history[-5:]
            if len(set(last_5)) == 1 and len(last_5) == 5:
                stuck_emotion = last_5[0]
                print(f"\n   ⚠️ PROBLEMA DETECTADO: Sistema ATASCADO en '{stuck_emotion}'")
                print(f"      Las últimas 5 fusiones son todas '{stuck_emotion}'")
                print(f"      Esto causará que rechace cualquier cambio (outlier penalty)")

        # Persistencia
        persistence = history_data.get("persistence")
        if persistence:
            print(f"\n   💾 PERSISTENCIA EMOCIONAL:")
            print(f"      Última emoción fuerte: {persistence.get('last_strong_emotion')}")
            print(f"      Confianza (con decay): {persistence.get('last_strong_confidence', 0):.2f}")

    # 2. Buffer stats
    print("\n\n📦 BUFFER DE DETECCIONES:")
    print("-" * 80)
    buffer_stats = get_buffer_stats(room)
    if buffer_stats:
        face_count = buffer_stats.get("face_count", 0)
        audio_count = buffer_stats.get("audio_count", 0)
        latest_face = buffer_stats.get("latest_face")
        latest_audio = buffer_stats.get("latest_audio")

        print(f"   Face detections: {face_count}")
        if latest_face:
            print(f"      Última: {latest_face.get('label')} ({latest_face.get('score', 0):.2f})")

        print(f"   Audio detections: {audio_count}")
        if latest_audio:
            print(f"      Última: {latest_audio.get('label')} ({latest_audio.get('score', 0):.2f})")

    # 3. Configuración temporal
    print("\n\n⚙️ CONFIGURACIÓN DE SUAVIZADO TEMPORAL:")
    print("-" * 80)
    config = get_temporal_config()
    if config:
        enabled = config.get("enable_smoothing", True)
        persistence_enabled = config.get("enable_persistence", True)

        print(f"   Suavizado temporal: {'✅ HABILITADO' if enabled else '❌ DESHABILITADO'}")
        print(f"   Persistencia emocional: {'✅ HABILITADO' if persistence_enabled else '❌ DESHABILITADO'}")

        if enabled:
            print(f"\n   Parámetros de filtros:")
            print(f"      - Tiempo mínimo entre cambios: {config.get('min_emotion_duration_sec', 0)}s")
            print(f"      - Confianza mínima para cambio: {config.get('min_confidence_for_change', 0):.2f}")
            print(f"      - Penalty por cambio brusco: {config.get('sudden_change_penalty', 0):.2f} ({int((1-config.get('sudden_change_penalty', 1))*100)}% reducción)")
            print(f"      - Penalty por outlier: {config.get('outlier_penalty', 0):.2f} ({int((1-config.get('outlier_penalty', 1))*100)}% reducción)")
            print(f"      - Rechazar outliers débiles: {'SÍ' if config.get('weak_outlier_reject', False) else 'NO'}")

            # Detectar si los filtros son muy agresivos
            if config.get('min_emotion_duration_sec', 0) > 1.0:
                print(f"\n      ⚠️ Tiempo mínimo MUY ALTO ({config.get('min_emotion_duration_sec')}s)")
                print(f"         Recomendación: reducir a 0.5-1.0s")

            if config.get('outlier_penalty', 1) < 0.70:
                print(f"\n      ⚠️ Penalty de outlier MUY AGRESIVO ({config.get('outlier_penalty')})")
                print(f"         Recomendación: aumentar a 0.75-0.85")


def show_solutions_menu(room):
    """Muestra menú de soluciones"""
    print_header("SOLUCIONES DISPONIBLES")

    print("\n¿Qué deseas hacer?\n")
    print("  1) Limpiar historial y buffer (RECOMENDADO)")
    print("     → Resetea completamente el sistema de fusión")
    print("")
    print("  2) Deshabilitar suavizado temporal")
    print("     → Hace que la fusión sea 100% reactiva (sin filtros)")
    print("     → ⚠️ Puede causar cambios bruscos de emoción")
    print("")
    print("  3) Suavizar filtros temporales")
    print("     → Reduce agresividad de filtros pero los mantiene activos")
    print("     → Balance entre estabilidad y reactividad")
    print("")
    print("  4) Ver diagnóstico nuevamente")
    print("")
    print("  0) Salir")
    print("")

    choice = input("Opción: ").strip()

    if choice == "1":
        confirm = input(f"\n⚠️ Esto limpiará TODO el historial de fusión y buffer para room '{room}'. ¿Continuar? (s/N): ")
        if confirm.lower() == 's':
            clear_buffer(room)

    elif choice == "2":
        confirm = input("\n⚠️ Esto deshabilitará el suavizado temporal. ¿Continuar? (s/N): ")
        if confirm.lower() == 's':
            disable_temporal_smoothing()

    elif choice == "3":
        confirm = input("\n⚠️ Esto ajustará los parámetros de filtrado. ¿Continuar? (s/N): ")
        if confirm.lower() == 's':
            make_filters_less_aggressive()

    elif choice == "4":
        diagnose(room)
        return show_solutions_menu(room)

    elif choice == "0":
        print("\n👋 Saliendo...\n")
        return

    else:
        print("\n❌ Opción inválida")
        return show_solutions_menu(room)


def main():
    room = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOM

    # Ejecutar diagnóstico
    diagnose(room)

    # Mostrar menú de soluciones
    show_solutions_menu(room)


if __name__ == "__main__":
    main()
