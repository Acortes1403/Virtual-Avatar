# app/routers/services/yolov8_face_emotion.py
from __future__ import annotations
import os
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from ultralytics import YOLO
import logging
import torch

logger = logging.getLogger("yolov8_emotion")

# Emotion classes matching the trained model
EMOTION_CLASSES = ['anger', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']

class YOLOv8FaceEmotion:
    """YOLOv8-based face emotion detection"""

    def __init__(self, model_path: str = None, conf_threshold: float = 0.45):
        """
        Initialize YOLOv8 emotion detector

        Args:
            model_path: Path to the trained YOLOv8 model (.pt file)
            conf_threshold: Minimum confidence threshold for detections (increased to 0.45 to reduce false positives)
        """
        self.conf_threshold = conf_threshold
        self.model = None
        self.model_path = model_path or self._get_default_model_path()

        # Load model
        self._load_model()

    def _get_default_model_path(self) -> str:
        """Get default model path"""
        base_dir = Path(__file__).parent.parent.parent  # emotion_api/app/
        model_path = base_dir / "models" / "yolov8_emotions.pt"
        return str(model_path)

    def _load_model(self):
        """Load the YOLOv8 model"""
        try:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model not found: {self.model_path}")

            logger.info(f"Loading YOLOv8 model from: {self.model_path}")

            # Handle PyTorch 2.6+ weights_only security feature
            try:
                # First try with safe globals for YOLOv8 model loading
                with torch.serialization.safe_globals([
                    'ultralytics.nn.tasks.DetectionModel',
                    'ultralytics.nn.modules.block.C2f',
                    'ultralytics.nn.modules.block.Bottleneck',
                    'ultralytics.nn.modules.conv.Conv',
                    'ultralytics.nn.modules.head.Detect',
                    'torch.nn.modules.container.ModuleList',
                    'torch.nn.modules.container.Sequential',
                ]):
                    self.model = YOLO(self.model_path)
            except Exception as safe_load_error:
                logger.warning(f"Safe loading failed: {safe_load_error}")
                logger.info("Attempting to load with weights_only=False (trusted model)")

                # Temporarily set environment variable to disable weights_only
                old_torch_load = torch.load
                def custom_load(*args, **kwargs):
                    kwargs['weights_only'] = False
                    return old_torch_load(*args, **kwargs)

                torch.load = custom_load
                try:
                    self.model = YOLO(self.model_path)
                finally:
                    torch.load = old_torch_load

            logger.info("YOLOv8 model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load YOLOv8 model: {e}")
            raise

    def predict(self, image: np.ndarray, size: int = 640) -> Dict:
        """
        Predict emotions from image using YOLOv8

        Args:
            image: BGR image array
            size: Input size for the model

        Returns:
            Dictionary with detection results
        """
        try:
            if self.model is None:
                raise RuntimeError("Model not loaded")

            # Run YOLOv8 inference
            results = self.model(image, conf=self.conf_threshold, imgsz=size, verbose=False)

            # Process results
            detections = []

            for result in results:
                if result.boxes is not None:
                    boxes = result.boxes

                    for i, box in enumerate(boxes):
                        # Get class ID and confidence
                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])

                        # Get emotion label
                        if 0 <= class_id < len(EMOTION_CLASSES):
                            emotion = EMOTION_CLASSES[class_id]
                        else:
                            emotion = "unknown"

                        # Get bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].tolist()

                        detections.append({
                            "label": emotion,
                            "score": confidence,
                            "bbox": [x1, y1, x2, y2],
                            "class_id": class_id
                        })

            # Sort by confidence (highest first)
            detections.sort(key=lambda x: x["score"], reverse=True)

            # Prepare response in expected format
            if detections:
                # Get the highest confidence detection
                top_detection = detections[0]

                # Create scores list for all detections
                scores = [{"label": det["label"], "score": det["score"]} for det in detections]

                return {
                    "label": top_detection["label"],
                    "score": top_detection["score"],
                    "scores": scores,
                    "debug": {
                        "total_detections": len(detections),
                        "model_confidence_threshold": self.conf_threshold,
                        "input_size": size,
                        "detections": detections
                    }
                }
            else:
                # No face/emotion detected
                return {
                    "label": "neutral",
                    "score": 0.0,
                    "scores": [{"label": "neutral", "score": 0.0}],
                    "debug": {
                        "total_detections": 0,
                        "model_confidence_threshold": self.conf_threshold,
                        "input_size": size,
                        "message": "No faces detected"
                    }
                }

        except Exception as e:
            logger.error(f"YOLOv8 prediction failed: {e}")
            raise

# Global model instance (singleton pattern)
_model_instance: Optional[YOLOv8FaceEmotion] = None

def get_yolov8_model() -> YOLOv8FaceEmotion:
    """Get singleton YOLOv8 model instance"""
    global _model_instance
    if _model_instance is None:
        _model_instance = YOLOv8FaceEmotion()
    return _model_instance

def classify_face_emotion_yolov8(image_bgr: np.ndarray, size: int = 640) -> Dict:
    """
    Classify face emotion using YOLOv8 model

    Args:
        image_bgr: BGR image array
        size: Input size for the model

    Returns:
        Dictionary with emotion classification results
    """
    model = get_yolov8_model()
    return model.predict(image_bgr, size=size)