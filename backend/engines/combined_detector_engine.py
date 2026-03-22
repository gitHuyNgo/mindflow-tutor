import asyncio
import base64
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import cv2
import numpy as np

from engines.attention_system.DistractDetector import DistractionDetector
from engines.confusion_system.noptConfuseDetector import ConfuseDetector

logger = logging.getLogger(__name__)

COOLDOWN_SECONDS = 5.0   # minimum gap between any two triggers


class CombinedDetectorEngine:
    """Backend engine that combines distraction and confusion detection from a frame."""

    def __init__(self):
        self.confuse_detector = ConfuseDetector(
            confuse_threshold=5,
            recover_threshold=3,
            clear_threshold=1,
        )
        self.distract_detector = DistractionDetector()
        self._last_trigger_time: float = 0.0   # epoch time of last fired event

    # ── helpers ────────────────────────────────────────────────────────────────

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

    def reset(self):
        """Reset both detectors and the cooldown timer to initial state."""
        # ── ConfuseDetector internals ──
        self.confuse_detector.confused_elapsed = 0.0
        self.confuse_detector.confused_since   = None
        self.confuse_detector.recover_start_time = None
        self.confuse_detector.is_confused      = False
        self.confuse_detector._face_cache      = None
        self.confuse_detector._frame_count     = 0
        if hasattr(self.confuse_detector, "clear_start_time"):
            self.confuse_detector.clear_start_time = None

        # ── DistractionDetector internals ──
        self.distract_detector.away_start       = None
        self.distract_detector.episode_history  = []
        self.distract_detector.triggered        = False
        self.distract_detector.long_triggered   = False

        # ── restart cooldown from now so nothing fires for COOLDOWN_SECONDS ──
        self._last_trigger_time = time.time()
        logger.info("CombinedDetectorEngine: reset + cooldown started")

    # ── detection ──────────────────────────────────────────────────────────────

    def detect_from_base64(self, image_base64: str) -> dict:
        frame_bgr = self._decode_frame(image_base64)

        distracted, face_is_centered, eye_is_centered = (
            self.distract_detector.detect_distraction(frame_bgr)
        )

        confused = False
        emotion = None
        if face_is_centered and eye_is_centered:
            confused, emotion = self.confuse_detector.detect_confusion(
                frame_bgr, draw=False
            )

        # ── cooldown gate ──────────────────────────────────────────────────────
        now = time.time()
        in_cooldown = (now - self._last_trigger_time) < COOLDOWN_SECONDS

        if in_cooldown:
            confused   = False
            distracted = False
        elif confused or distracted:
            # fire event → reset everything + start new cooldown
            self.reset()

        result = {
            "success":    True,
            "confused":   bool(confused),
            "distracted": bool(distracted),
        }

        logger.info(
            json.dumps(
                {
                    "event":      "frame_detection",
                    "ts":         datetime.now(timezone.utc).isoformat(),
                    "in_cooldown": in_cooldown,
                    **result,
                }
            )
        )

        return result

    async def detect_from_base64_async(self, image_base64: str) -> dict:
        """Non-blocking version — runs heavy CV work in a thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.detect_from_base64, image_base64)


_combined_detector_engine: Optional[CombinedDetectorEngine] = None


def get_combined_detector_engine() -> CombinedDetectorEngine:
    global _combined_detector_engine
    if _combined_detector_engine is None:
        _combined_detector_engine = CombinedDetectorEngine()
    return _combined_detector_engine

