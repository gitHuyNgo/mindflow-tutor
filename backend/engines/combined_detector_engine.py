import base64
import logging
from typing import Optional

import cv2
import numpy as np

from engines.attention_system.DistractDetector import DistractionDetector
from engines.confusion_system.noptConfuseDetector import ConfuseDetector

logger = logging.getLogger(__name__)


class CombinedDetectorEngine:
    """Backend engine that combines distraction and confusion detection from a frame."""

    def __init__(self):
        self.confuse_detector = ConfuseDetector(
            confuse_threshold=5,
            recover_threshold=3,
            clear_threshold=1,
        )
        self.distract_detector = DistractionDetector()

    @staticmethod
    def _decode_frame(image_base64: str) -> np.ndarray:
        if not image_base64:
            raise ValueError("image_base64 is required")

        payload = image_base64.split(",", 1)[1] if "," in image_base64 else image_base64
        raw = base64.b64decode(payload)
        arr = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if frame is None:
            raise ValueError("Unable to decode image_base64 into an image frame")

        return frame

    def detect_from_base64(self, image_base64: str) -> dict:
        frame_bgr = self._decode_frame(image_base64)

        distracted, is_centered = self.distract_detector.detect_distraction(frame_bgr)

        confused = False
        if is_centered:
            confused = self.confuse_detector.detect_confusion(frame_bgr)

        return {
            "success": True,
            "confused": bool(confused),
            "distracted": bool(distracted),
            "is_centered": bool(is_centered),
        }


_combined_detector_engine: Optional[CombinedDetectorEngine] = None


def get_combined_detector_engine() -> CombinedDetectorEngine:
    global _combined_detector_engine
    if _combined_detector_engine is None:
        _combined_detector_engine = CombinedDetectorEngine()
    return _combined_detector_engine
