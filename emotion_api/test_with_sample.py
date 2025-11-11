#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar el modelo Whisper con sample.wav
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.routers.services.whisper_speech_emotion import classify_speech_emotion_whisper

def test_with_sample():
    """Prueba el modelo con el archivo sample.wav"""
    sample_path = "sample.wav"

    print("Probando modelo Whisper con sample.wav...")
    print(f"Archivo: {sample_path}")

    if not os.path.exists(sample_path):
        print(f"ERROR: No se encontro el archivo: {sample_path}")
        return False

    try:
        # Obtener información del archivo
        file_size = os.path.getsize(sample_path)
        print(f"Tamaño del archivo: {file_size} bytes")

        # Ejecutar clasificación
        print("Ejecutando clasificacion de emociones...")
        result = classify_speech_emotion_whisper(sample_path)

        print("\nClasificacion completada!")
        print("=" * 50)
        print(f"Emocion principal: {result['label']}")
        print(f"Confianza: {result['score']:.3f} ({result['score']*100:.1f}%)")
        print(f"Modelo: {result['model']}")

        print("\nTodas las emociones detectadas:")
        for i, emotion in enumerate(result['scores'][:7], 1):
            bar_length = int(emotion['score'] * 20)
            bar = "#" * bar_length + "-" * (20 - bar_length)
            print(f"  {i}. {emotion['label']:>10s}: {bar} {emotion['score']:.3f}")

        if result['debug']:
            print(f"\nDebug info:")
            for key, value in result['debug'].items():
                print(f"   - {key}: {value}")

        return True

    except Exception as e:
        print(f"ERROR durante la clasificacion: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Prueba del modelo Whisper Speech Emotion con sample.wav")
    print("=" * 60)

    success = test_with_sample()

    print("\n" + "=" * 60)
    if success:
        print("Prueba completada exitosamente!")
    else:
        print("La prueba fallo.")
        print("Verifica que las dependencias esten instaladas:")
        print("   pip install librosa transformers torch")

    sys.exit(0 if success else 1)