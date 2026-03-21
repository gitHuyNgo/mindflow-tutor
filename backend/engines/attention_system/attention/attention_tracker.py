import numpy as np


class AttentionTracker:

    def __init__(self):

        self.left_eye = [33, 133]
        self.right_eye = [362, 263]

        self.left_iris = 468
        self.right_iris = 473

    def get_eye_direction(self, landmarks):

        left_eye_left = landmarks.landmark[self.left_eye[0]].x
        left_eye_right = landmarks.landmark[self.left_eye[1]].x

        iris = landmarks.landmark[self.left_iris].x

        ratio = (iris - left_eye_left) / (left_eye_right - left_eye_left + 1e-6)

        if ratio < 0.35:
            return "right"

        elif ratio > 0.65:
            return "left"

        return "center"
