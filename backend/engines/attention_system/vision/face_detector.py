import os
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks_python
from mediapipe.tasks.python import vision as mp_tasks_vision

_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
_MODEL_PATH = os.path.join(os.path.expanduser("~"), ".mediapipe", "face_landmarker.task")


def _ensure_model():
    os.makedirs(os.path.dirname(_MODEL_PATH), exist_ok=True)
    if not os.path.isfile(_MODEL_PATH):
        print(f"Downloading face landmarker model to {_MODEL_PATH} ...")
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)


class _LandmarkWrapper:
    """Wraps new Tasks API landmark list to match legacy `.landmark[i].x` access."""
    def __init__(self, landmarks):
        self.landmark = landmarks


class FaceDetector:

    def __init__(self):
        _ensure_model()
        base_options = mp_tasks_python.BaseOptions(model_asset_path=_MODEL_PATH)
        options = mp_tasks_vision.FaceLandmarkerOptions(
            base_options=base_options,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.landmarker = mp_tasks_vision.FaceLandmarker.create_from_options(options)

    def detect(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect(mp_image)

        if not result.face_landmarks:
            return None

        return _LandmarkWrapper(result.face_landmarks[0])
