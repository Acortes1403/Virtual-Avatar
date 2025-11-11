# app/routers/services/lstm_tess_emotion.py
"""
Speech Emotion Recognition using custom LSTM model trained on TESS dataset
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
MODEL_DIR = "models/lstm_tess"  # Path relative to emotion_api root
MODEL_PATH = os.path.join(MODEL_DIR, "best_model.keras")
LABEL_ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoder.pkl")
METADATA_PATH = os.path.join(MODEL_DIR, "model_metadata.json")

# Audio processing configuration (must match training config)
SAMPLE_RATE = 16000
N_MFCC = 40
DURATION = 3
OFFSET = 0.5


class LSTMTESSEmotionModel:
    """Custom LSTM model trained on TESS dataset for emotion recognition"""

    def __init__(self):
        self.model = None
        self.label_encoder = None
        self.metadata = None
        self._load_model()

    def _load_model(self):
        """Load the trained LSTM model and label encoder"""
        try:
            # Get absolute paths
            current_dir = os.path.dirname(os.path.abspath(__file__))
            api_root = os.path.join(current_dir, "..", "..", "..")

            model_path = os.path.join(api_root, MODEL_PATH)
            encoder_path = os.path.join(api_root, LABEL_ENCODER_PATH)
            metadata_path = os.path.join(api_root, METADATA_PATH)

            logger.info(f"Loading LSTM model from: {model_path}")

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
                logger.info("Model metadata loaded")
            except Exception as e:
                logger.warning(f"Could not load metadata: {e}")
                self.metadata = {}

        except Exception as e:
            logger.error(f"Failed to load LSTM TESS model: {e}")
            raise RuntimeError(f"Could not load LSTM emotion model: {e}")

    def _preprocess_audio(self, audio_path: str) -> np.ndarray:
        """
        Preprocess audio file to extract MFCC features

        Args:
            audio_path: Path to audio file

        Returns:
            MFCC feature vector
        """
        try:
            # Load audio
            y, sr = librosa.load(
                audio_path,
                duration=DURATION,
                offset=OFFSET,
                sr=SAMPLE_RATE
            )

            # Extract MFCC features
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC)

            # Average across time (same as training)
            mfcc_mean = np.mean(mfcc.T, axis=0)

            # Reshape for LSTM input: (batch_size, timesteps, features)
            mfcc_input = np.expand_dims(mfcc_mean, axis=-1)  # Add channel dim
            mfcc_input = np.expand_dims(mfcc_input, axis=0)   # Add batch dim

            logger.debug(f"MFCC features extracted: shape={mfcc_input.shape}")
            return mfcc_input

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
            features = self._preprocess_audio(audio_path)

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
                "model": "lstm-tess-custom",
                "model_info": {
                    "type": "LSTM",
                    "dataset": "TESS",
                    "train_accuracy": self.metadata.get("train_accuracy", "N/A"),
                    "val_accuracy": self.metadata.get("val_accuracy", "N/A")
                },
                "debug": {
                    "total_emotions": len(all_scores),
                    "predicted_class_idx": int(predicted_class_idx),
                    "feature_shape": features.shape,
                    "confidence_threshold": 0.5
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
                "model": "lstm-tess-custom",
                "model_info": {"type": "LSTM", "dataset": "TESS"},
                "debug": {"error": str(e), "fallback": True}
            }


# Global model instance (singleton pattern)
_model_instance = None


def get_lstm_tess_model() -> LSTMTESSEmotionModel:
    """Get singleton instance of the LSTM TESS model"""
    global _model_instance
    if _model_instance is None:
        _model_instance = LSTMTESSEmotionModel()
    return _model_instance


def classify_speech_emotion_lstm_tess(audio_path: str) -> Dict[str, Any]:
    """
    Main function to classify speech emotion using LSTM TESS model

    Args:
        audio_path: Path to audio file

    Returns:
        Dictionary with emotion classification results
    """
    model = get_lstm_tess_model()
    return model.predict_emotion(audio_path)
