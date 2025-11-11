# app/routers/services/lstm_crema_emotion.py
"""
Speech Emotion Recognition using LSTM model trained on CREMA-D dataset V3
Enhanced version with CNN-BiLSTM-Attention architecture
"""

import logging
import librosa
import numpy as np
import pickle
import os
from typing import Dict, List, Any
from tensorflow import keras

logger = logging.getLogger(__name__)

# Model configuration
MODEL_DIR = "models/lstm_crema_v3"  # Path relative to emotion_api root
MODEL_PATH = os.path.join(MODEL_DIR, "best_model.keras")
LABEL_ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoder.pkl")
METADATA_PATH = os.path.join(MODEL_DIR, "model_metadata.json")

# Audio processing configuration (V3 advanced features)
SAMPLE_RATE = 22050
MAX_PAD_LEN = 130
DURATION = 3.0


class LSTMCremaEmotionModel:
    """LSTM model trained on CREMA-D dataset for emotion recognition"""

    def __init__(self):
        self.model = None
        self.label_encoder = None
        self.metadata = None
        self._load_model()

    def _load_model(self):
        """Load the trained LSTM CREMA-D model and label encoder"""
        try:
            # Get absolute paths
            current_dir = os.path.dirname(os.path.abspath(__file__))
            api_root = os.path.join(current_dir, "..", "..", "..")

            model_path = os.path.join(api_root, MODEL_PATH)
            encoder_path = os.path.join(api_root, LABEL_ENCODER_PATH)
            metadata_path = os.path.join(api_root, METADATA_PATH)

            logger.info(f"Loading LSTM CREMA-D V3 model from: {model_path}")

            # Load model
            self.model = keras.models.load_model(model_path)
            logger.info("Model loaded successfully")

            # Load label encoder
            with open(encoder_path, 'rb') as f:
                self.label_encoder = pickle.load(f)
            logger.info(f"Label encoder loaded: {self.label_encoder.classes_}")

            # Load metadata (optional)
            try:
                import json
                with open(metadata_path, 'r') as f:
                    self.metadata = json.load(f)
                logger.info(f"Model metadata loaded (V3 - Test Accuracy: {self.metadata.get('test_accuracy', 'N/A')})")
            except Exception as e:
                logger.warning(f"Could not load metadata: {e}")
                self.metadata = {}

        except Exception as e:
            logger.error(f"Failed to load LSTM CREMA-D model: {e}")
            raise RuntimeError(f"Could not load LSTM emotion model: {e}")

    def _extract_features_advanced(self, audio_path: str) -> np.ndarray:
        """
        Extract advanced features from audio file (V3 method)
        - MFCC
        - Chroma
        - Mel Spectrogram
        - Spectral Contrast
        """
        try:
            # Load audio
            y, sr = librosa.load(audio_path, duration=DURATION, sr=SAMPLE_RATE)

            # 1. MFCC
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
            mfcc = np.pad(mfcc, ((0, 0), (0, max(0, MAX_PAD_LEN - mfcc.shape[1]))), mode='constant')
            mfcc = mfcc[:, :MAX_PAD_LEN]

            # 2. Chroma
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            chroma = np.pad(chroma, ((0, 0), (0, max(0, MAX_PAD_LEN - chroma.shape[1]))), mode='constant')
            chroma = chroma[:, :MAX_PAD_LEN]

            # 3. Mel Spectrogram
            mel = librosa.feature.melspectrogram(y=y, sr=sr)
            mel = np.pad(mel, ((0, 0), (0, max(0, MAX_PAD_LEN - mel.shape[1]))), mode='constant')
            mel = mel[:, :MAX_PAD_LEN]

            # 4. Spectral Contrast
            contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
            contrast = np.pad(contrast, ((0, 0), (0, max(0, MAX_PAD_LEN - contrast.shape[1]))), mode='constant')
            contrast = contrast[:, :MAX_PAD_LEN]

            # Combine all features
            features = np.vstack([mfcc, chroma, mel, contrast])

            # Transpose for LSTM: (timesteps, features)
            features = features.T

            # Add batch dimension: (1, timesteps, features)
            features = np.expand_dims(features, axis=0)

            logger.debug(f"Advanced features extracted: shape={features.shape}")
            return features

        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            raise ValueError(f"Could not extract features: {e}")

    def predict_emotion(self, audio_path: str) -> Dict[str, Any]:
        """
        Predict emotion from audio file using CREMA-D V3 model

        Args:
            audio_path: Path to audio file

        Returns:
            Dictionary with emotion prediction results
        """
        try:
            # Extract features
            features = self._extract_features_advanced(audio_path)

            # Make prediction
            predictions = self.model.predict(features, verbose=0)

            # Get predicted class
            predicted_class_idx = np.argmax(predictions[0])
            predicted_label = self.label_encoder.classes_[predicted_class_idx]
            predicted_score = float(predictions[0][predicted_class_idx])

            # Get all emotion scores
            all_scores = []
            for idx, prob in enumerate(predictions[0]):
                emotion_label = self.label_encoder.classes_[idx]
                all_scores.append({
                    "label": emotion_label,
                    "score": float(prob)
                })

            # Sort by score (highest first)
            all_scores.sort(key=lambda x: x["score"], reverse=True)

            result = {
                "label": predicted_label,
                "score": predicted_score,
                "scores": all_scores,
                "model": "lstm-crema-v3",
                "model_info": {
                    "type": "CNN-BiLSTM-Attention",
                    "dataset": "CREMA-D",
                    "version": "v3",
                    "test_accuracy": self.metadata.get("test_accuracy", 0.6285),
                    "sample_rate": SAMPLE_RATE,
                    "features": "MFCC+Chroma+Mel+Contrast"
                },
                "debug": {
                    "total_emotions": len(all_scores),
                    "predicted_class_idx": int(predicted_class_idx),
                    "feature_shape": str(features.shape),
                    "model_version": "v3"
                }
            }

            logger.info(f"Emotion prediction (CREMA-V3): {predicted_label} ({predicted_score:.3f})")
            return result

        except Exception as e:
            logger.error(f"Emotion prediction failed: {e}")
            # Return neutral fallback
            return {
                "label": "neutral",
                "score": 0.5,
                "scores": [{"label": "neutral", "score": 0.5}],
                "model": "lstm-crema-v3",
                "model_info": {
                    "type": "CNN-BiLSTM-Attention",
                    "dataset": "CREMA-D",
                    "version": "v3"
                },
                "debug": {"error": str(e), "fallback": True}
            }


# Global model instance (singleton pattern)
_model_instance = None


def get_lstm_crema_model() -> LSTMCremaEmotionModel:
    """Get singleton instance of the LSTM CREMA-D model"""
    global _model_instance
    if _model_instance is None:
        _model_instance = LSTMCremaEmotionModel()
    return _model_instance


def classify_speech_emotion_lstm_crema(audio_path: str) -> Dict[str, Any]:
    """
    Main function to classify speech emotion using LSTM CREMA-D V3 model

    Args:
        audio_path: Path to audio file

    Returns:
        Dictionary with emotion classification results
    """
    model = get_lstm_crema_model()
    return model.predict_emotion(audio_path)
