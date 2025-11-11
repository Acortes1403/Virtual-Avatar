"""
Script de prueba para verificar la integración del modelo LSTM TESS
"""

import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(__file__))

from app.routers.services.lstm_tess_emotion import classify_speech_emotion_lstm_tess

def test_lstm_model():
    """Test básico del modelo LSTM"""

    print("=" * 60)
    print("TEST: Integración del Modelo LSTM TESS")
    print("=" * 60)

    # 1. Verificar que los archivos del modelo existen
    print("\n1. Verificando archivos del modelo...")
    model_files = [
        "models/lstm_tess/best_model.keras",
        "models/lstm_tess/label_encoder.pkl",
        "models/lstm_tess/model_metadata.json"
    ]

    for file in model_files:
        if os.path.exists(file):
            size = os.path.getsize(file) / 1024
            print(f"   ✓ {file} ({size:.1f} KB)")
        else:
            print(f"   ✗ {file} - NO ENCONTRADO")
            return False

    # 2. Intentar cargar el modelo
    print("\n2. Cargando modelo LSTM...")
    try:
        from app.routers.services.lstm_tess_emotion import get_lstm_tess_model
        model = get_lstm_tess_model()
        print(f"   ✓ Modelo cargado exitosamente")
        print(f"   ✓ Clases: {model.label_encoder.classes_}")
        if model.metadata:
            print(f"   ✓ Precisión de entrenamiento: {model.metadata.get('train_accuracy', 'N/A')}")
            print(f"   ✓ Precisión de validación: {model.metadata.get('val_accuracy', 'N/A')}")
    except Exception as e:
        print(f"   ✗ Error al cargar modelo: {e}")
        return False

    # 3. Probar con archivo de audio de ejemplo
    print("\n3. Probando con archivo de audio...")
    sample_path = "sample.wav"

    if not os.path.exists(sample_path):
        print(f"   ⚠ Archivo de ejemplo no encontrado: {sample_path}")
        print("   Saltando prueba con audio...")
    else:
        try:
            result = classify_speech_emotion_lstm_tess(sample_path)
            print(f"   ✓ Predicción exitosa:")
            print(f"      - Emoción: {result['label']}")
            print(f"      - Confianza: {result['score']*100:.2f}%")
            print(f"      - Modelo: {result['model']}")

            print(f"\n   📊 Top 3 emociones:")
            for i, score in enumerate(result['scores'][:3], 1):
                print(f"      {i}. {score['label']}: {score['score']*100:.2f}%")

        except Exception as e:
            print(f"   ✗ Error al clasificar audio: {e}")
            import traceback
            traceback.print_exc()
            return False

    print("\n" + "=" * 60)
    print("✅ PRUEBA COMPLETADA EXITOSAMENTE")
    print("=" * 60)
    print("\nEl modelo LSTM TESS está correctamente integrado.")
    print("Ahora puedes usarlo en el endpoint /emotion/from-speech")

    return True

if __name__ == "__main__":
    success = test_lstm_model()
    sys.exit(0 if success else 1)
