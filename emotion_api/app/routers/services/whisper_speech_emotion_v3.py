# app/routers/services/whisper_speech_emotion_v3.py
"""
Speech Emotion Recognition using Whisper Large V3
Based on: https://huggingface.co/firdhokk/speech-emotion-recognition-with-openai-whisper-large-v3
"""

import logging
import librosa
import torch
import numpy as np
from typing import Dict, List, Any
from transformers import AutoModelForAudioClassification, AutoFeatureExtractor

logger = logging.getLogger(__name__)

# Model configuration
MODEL_ID = "firdhokk/speech-emotion-recognition-with-openai-whisper-large-v3"

# Expected emotion labels from the model
EMOTION_LABELS = {
    0: "angry",
    1: "disgust",
    2: "fearful",
    3: "happy",
    4: "neutral",
    5: "sad",
    6: "surprised"
}

class WhisperSpeechEmotionV3:
    """Speech Emotion Recognition using Whisper Large V3 model"""

    def __init__(self):
        self.model = None
        self.feature_extractor = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_model()

    def _load_model(self):
        """Load the Whisper Large V3 model and feature extractor"""
        try:
            logger.info(f"Loading Whisper Large V3 model: {MODEL_ID}")
            self.model = AutoModelForAudioClassification.from_pretrained(MODEL_ID)
            self.feature_extractor = AutoFeatureExtractor.from_pretrained(MODEL_ID)

            # Move model to appropriate device
            self.model.to(self.device)
            self.model.eval()  # Set to evaluation mode

            logger.info(f"Model loaded successfully on device: {self.device}")

        except Exception as e:
            logger.error(f"Failed to load Whisper Large V3 model: {e}")
            raise RuntimeError(f"Could not load speech emotion model: {e}")

    def _preprocess_audio(self, audio_path: str) -> np.ndarray:
        """
        Preprocess audio file using librosa

        Args:
            audio_path: Path to audio file

        Returns:
            Preprocessed audio array
        """
        try:
            # Load audio file with librosa (16kHz sampling rate as expected by Whisper)
            audio, sample_rate = librosa.load(audio_path, sr=16000)

            # Ensure audio is not empty
            if len(audio) == 0:
                raise ValueError("Audio file is empty")

            # Normalize audio
            audio = librosa.util.normalize(audio)

            logger.debug(f"Audio preprocessed: shape={audio.shape}, sample_rate={sample_rate}")
            return audio

        except Exception as e:
            logger.error(f"Audio preprocessing failed: {e}")
            raise ValueError(f"Could not preprocess audio: {e}")

    def predict_emotion(self, audio_path: str) -> Dict[str, Any]:
        """
        Predict emotion from audio file

        Args:
            audio_path: Path to audio file

        Returns:
            Dictionary with emotion prediction results
        """
        try:
            # Preprocess audio
            audio = self._preprocess_audio(audio_path)

            # Extract features using the feature extractor
            inputs = self.feature_extractor(
                audio,
                sampling_rate=16000,
                return_tensors="pt"
            )

            # Move inputs to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Make prediction
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits

                # Apply softmax to get probabilities
                probabilities = torch.nn.functional.softmax(logits, dim=-1)

                # Get predictions
                predicted_class_id = logits.argmax(-1).item()
                predicted_label = EMOTION_LABELS.get(predicted_class_id, "unknown")
                predicted_score = probabilities[0][predicted_class_id].item()

                # Get all emotion scores
                all_scores = []
                for i, prob in enumerate(probabilities[0]):
                    emotion_label = EMOTION_LABELS.get(i, f"emotion_{i}")
                    all_scores.append({
                        "label": emotion_label,
                        "score": prob.item()
                    })

                # Sort by score (highest first)
                all_scores.sort(key=lambda x: x["score"], reverse=True)

                result = {
                    "label": predicted_label,
                    "score": predicted_score,
                    "scores": all_scores,
                    "model": "whisper-large-v3-speech-emotion",
                    "device": str(self.device),
                    "debug": {
                        "total_emotions": len(all_scores),
                        "predicted_class_id": predicted_class_id,
                        "audio_shape": audio.shape,
                        "confidence_threshold": 0.5  # You can adjust this
                    }
                }

                logger.info(f"Emotion prediction: {predicted_label} ({predicted_score:.3f})")
                return result

        except Exception as e:
            logger.error(f"Emotion prediction failed: {e}")
            # Return neutral fallback
            return {
                "label": "neutral",
                "score": 0.5,
                "scores": [{"label": "neutral", "score": 0.5}],
                "model": "whisper-large-v3-speech-emotion",
                "device": str(self.device),
                "debug": {"error": str(e), "fallback": True}
            }

# Global model instance (singleton pattern)
_model_instance = None

def get_whisper_speech_emotion_v3_model() -> WhisperSpeechEmotionV3:
    """Get singleton instance of the Whisper Large V3 model"""
    global _model_instance
    if _model_instance is None:
        _model_instance = WhisperSpeechEmotionV3()
    return _model_instance

def classify_speech_emotion_whisper_v3(audio_path: str) -> Dict[str, Any]:
    """
    Main function to classify speech emotion using Whisper Large V3

    Args:
        audio_path: Path to audio file

    Returns:
        Dictionary with emotion classification results
    """
    model = get_whisper_speech_emotion_v3_model()
    return model.predict_emotion(audio_path)