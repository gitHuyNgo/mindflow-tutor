import cv2
import time

from .vision.face_detector import FaceDetector
from .vision.head_pose import HeadPoseEstimator

from .attention.attention_tracker import AttentionTracker
from .attention.distraction_detector import DistractionDetector as DistractionState


class DistractionDetector():
    def __init__(self):
        self.face_detector = FaceDetector()
        self.head_pose = HeadPoseEstimator()
        self.eye_tracker = AttentionTracker()
        self.distraction_state = DistractionState()

    def detect_distraction(self, frame):
        face_detector = self.face_detector
        head_pose = self.head_pose
        eye_tracker = self.eye_tracker
        distraction = self.distraction_state

        landmarks = face_detector.detect(frame)

        distracted = False

        head_dir = True
        if landmarks:

            head_dir = head_pose.estimate(frame, landmarks)

            eye_dir = eye_tracker.get_eye_direction(landmarks)

            if head_dir != "center":
                distracted = True

            if eye_dir != "center":
                distracted = True
            if distraction.away_start:
                away_time = time.time() - distraction.away_start
            else:
                away_time = 0

        notify = distraction.update(distracted)

        return notify, head_dir == "center", eye_dir == "center"
