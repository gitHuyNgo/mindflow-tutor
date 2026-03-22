import cv2

from .vision.face_detector import FaceDetector
from .vision.head_pose import HeadPoseEstimator

from .attention.distraction_detector import DistractionDetector as DistractionState


class DistractionDetector():
    def __init__(self):
        self.face_detector = FaceDetector()
        self.head_pose = HeadPoseEstimator()
        self.distraction_state = DistractionState()

    def detect_distraction(self, frame):
        face_detector = self.face_detector
        head_pose = self.head_pose
        distraction = self.distraction_state

        landmarks = face_detector.detect(frame)

        distracted = False

        head_dir = "center"
        if landmarks:
            head_dir = head_pose.estimate(frame, landmarks)

            if head_dir != "center":
                distracted = True

        notify = distraction.update(distracted)

        return notify, head_dir == "center", True
