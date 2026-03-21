import numpy as np
import cv2


class HeadPoseEstimator:

    def __init__(self):

        self.model_points = np.array([
            (0.0, 0.0, 0.0),
            (0.0, -330.0, -65.0),
            (-225.0, 170.0, -135.0),
            (225.0, 170.0, -135.0),
            (-150.0, -150.0, -125.0),
            (150.0, -150.0, -125.0)
        ])

    def estimate(self, frame, landmarks):

        h, w = frame.shape[:2]

        image_points = np.array([

            (landmarks.landmark[1].x * w, landmarks.landmark[1].y * h),
            (landmarks.landmark[152].x * w, landmarks.landmark[152].y * h),
            (landmarks.landmark[33].x * w, landmarks.landmark[33].y * h),
            (landmarks.landmark[263].x * w, landmarks.landmark[263].y * h),
            (landmarks.landmark[61].x * w, landmarks.landmark[61].y * h),
            (landmarks.landmark[291].x * w, landmarks.landmark[291].y * h)

        ], dtype="double")

        focal_length = w
        center = (w/2, h/2)

        camera_matrix = np.array(
            [[focal_length, 0, center[0]],
             [0, focal_length, center[1]],
             [0, 0, 1]],
            dtype="double"
        )

        dist_coeffs = np.zeros((4, 1))

        success, rotation_vector, translation_vector = cv2.solvePnP(
            self.model_points,
            image_points,
            camera_matrix,
            dist_coeffs
        )

        rmat, _ = cv2.Rodrigues(rotation_vector)

        angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)

        pitch, yaw, roll = angles

        if yaw > 20:
            direction = "right"

        elif yaw < -20:
            direction = "left"

        else:
            direction = "center"

        return direction
