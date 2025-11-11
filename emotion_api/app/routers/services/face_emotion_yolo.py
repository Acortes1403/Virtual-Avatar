# app/routers/services/face_emotion_yolo.py
from __future__ import annotations
import os
import cv2
import numpy as np
import onnxruntime as ort
from typing import List, Dict, Tuple

FER7 = ["anger", "disgust", "fear", "happy", "neutral", "sad", "surprise"]

def letterbox(img: np.ndarray,
              new_shape: Tuple[int, int],
              color=(114,114,114),
              auto: bool = False) -> Tuple[np.ndarray, Tuple[float,float], Tuple[int,int]]:
    """
    Versión simple: si auto=False, fuerza EXACTAMENTE new_shape (H,W) con padding.
    Devuelve (img_pad, (r_x,r_y), (padx,pady)).
    """
    h, w = img.shape[:2]
    new_h, new_w = int(new_shape[0]), int(new_shape[1])
    r = min(new_w / w, new_h / h)
    # tamaño sin pad manteniendo aspecto
    nw, nh = int(round(w * r)), int(round(h * r))
    img = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    # padding para llegar EXACTO a (new_h,new_w)
    top = (new_h - nh) // 2
    bottom = new_h - nh - top
    left = (new_w - nw) // 2
    right = new_w - nw - left
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    gain = (r, r)
    pad = (left, top)
    return img, gain, pad

def xywh2xyxy(x: np.ndarray) -> np.ndarray:
    y = np.empty_like(x)
    y[:, 0] = x[:, 0] - x[:, 2] / 2
    y[:, 1] = x[:, 1] - x[:, 3] / 2
    y[:, 2] = x[:, 0] + x[:, 2] / 2
    y[:, 3] = x[:, 1] + x[:, 3] / 2
    return y

def nms(boxes: np.ndarray, scores: np.ndarray, iou_thres: float=0.45) -> List[int]:
    x1, y1, x2, y2 = boxes.T
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-7)
        inds = np.where(iou <= iou_thres)[0]
        order = order[inds + 1]
    return keep

class FaceEmotionYOLO:
    def __init__(self, onnx_path: str, providers: list[str] | None = None,
                 conf_thres: float | None = None, iou_thres: float | None = None):
        self.onnx_path = onnx_path
        self.providers = providers or ["CPUExecutionProvider"]
        self.nc = len(FER7)
        self.conf_thres = float(os.getenv("FACE_CONF_THRES", conf_thres or 0.25))
        self.iou_thres = float(os.getenv("FACE_IOU_THRES", iou_thres or 0.45))

        self.sess = ort.InferenceSession(self.onnx_path, providers=self.providers)
        self.inp = self.sess.get_inputs()[0]
        self.inp_name = self.inp.name
        self.out_name = self.sess.get_outputs()[0].name

        # Leer HxW esperados (1,3,H,W)
        ishape = self.inp.shape
        # cuando vienen como None, usa 640 por defecto; si vienen números, úsalos
        self.in_h = int(ishape[2] or 640)
        self.in_w = int(ishape[3] or 640)

    def _run(self, im: np.ndarray) -> np.ndarray:
        out = self.sess.run([self.out_name], {self.inp_name: im})[0]
        if out.ndim == 3:
            if out.shape[1] == (4 + self.nc):      # (1,84,N)
                out = np.transpose(out, (0, 2, 1))  # -> (1,N,84)
            out = out[0]
        elif out.ndim == 2:
            pass
        else:
            raise RuntimeError(f"Unexpected ONNX output shape: {out.shape}")
        return out  # (N, 4+nc)

    def predict(self, img_bgr: np.ndarray) -> List[Dict]:
        # Letterbox EXACTO al tamaño de entrada del modelo
        lb, gain, pad = letterbox(img_bgr, (self.in_h, self.in_w), auto=False)
        im = lb[:, :, ::-1].transpose(2, 0, 1).astype(np.float32) / 255.0
        im = im[None, ...]  # (1,3,H,W)

        preds = self._run(im)
        if preds.size == 0:
            return []

        boxes = preds[:, :4]              # cx,cy,w,h (en sistema HxW del modelo)
        cls = preds[:, 4:4+self.nc]

        # Si parecen logits, aplica sigmoid
        if cls.max() > 1.0 or cls.min() < 0.0:
            cls = 1 / (1 + np.exp(-cls))

        conf = cls.max(axis=1)
        cls_id = cls.argmax(axis=1)

        m = conf >= self.conf_thres
        if not np.any(m):
            return []

        boxes = boxes[m]
        conf = conf[m]
        cls_id = cls_id[m]

        boxes = xywh2xyxy(boxes)

        # Deshacer letterbox para recuperar coords en la imagen original
        boxes[:, [0, 2]] -= pad[0]
        boxes[:, [1, 3]] -= pad[1]
        boxes /= gain[0]

        # NMS por clase (offset)
        offsets = cls_id.astype(np.float32) * 4096.0
        keep = nms(boxes + offsets[:, None], conf, self.iou_thres)

        results: List[Dict] = []
        for i in keep:
            x1, y1, x2, y2 = boxes[i]
            results.append({
                "label": FER7[int(cls_id[i])],
                "score": float(conf[i]),
                "box": [float(x1), float(y1), float(x2), float(y2)],
            })
        return results
