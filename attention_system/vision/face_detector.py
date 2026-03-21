import mediapipe as mp
import cv2


class FaceDetector:

    def __init__(self):

        self.mp_face = mp.solutions.face_mesh

        self.face_mesh = self.mp_face.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def detect(self, frame):

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        result = self.face_mesh.process(rgb)

        if not result.multi_face_landmarks:
            return None

        return result.multi_face_landmarks[0]
