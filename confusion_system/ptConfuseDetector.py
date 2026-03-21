from pathlib import Path
import time
import numpy as np
import cv2
import torch
from facenet_pytorch import MTCNN
from hsemotion.facial_emotions import HSEmotionRecognizer

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
NORMAL_EMOTIONS = {'neutral', 'happiness', 'surprise'}
CONFUSED_EMOTIONS = {'sadness', 'anger', 'disgust', 'fear', 'contempt'}


class ConfuseDetector:
    def __init__(self, model_name="enet_b0_8_best_afew", confuse_threshold=5, recover_threshold=2, clear_threshold=1):
        self.CONFUSED_THRESHOLD_SECONDS = confuse_threshold
        self.RECOVER_GRACE_SECONDS = recover_threshold
        self.CLEAR_THRESHOLD_SECONDS = clear_threshold

        self.mtcnn = MTCNN(keep_all=False, post_process=False, min_face_size=40, device=DEVICE)
        self.model = HSEmotionRecognizer(model_name=model_name, device=DEVICE)
        
        self.confused_elapsed = 0.0 
        self.confused_since = None
        self.recover_start_time = None

    def detect_face(self, frame):
        bounding_boxes, probs = self.mtcnn.detect(frame, landmarks=False)
        if bounding_boxes is None or probs is None:
            return None
        filtered = bounding_boxes[probs > 0.9]
        if len(filtered) == 0:
            return None
        return filtered[0]

    def predict(self, face, frame_rgb):
        if face is None:
            return None
        x1, y1, x2, y2 = [int(v) for v in face]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(frame_rgb.shape[1], x2), min(frame_rgb.shape[0], y2)
        face_rgb = frame_rgb[y1:y2, x1:x2]
        if face_rgb.size == 0:
            return None
        emotion, _ = self.model.predict_emotions(face_rgb, logits=True)
        return emotion.lower()


    def check_focus(self, emotion):
        now = time.time()

        if emotion in CONFUSED_EMOTIONS:
            self.recover_start_time = None
            self.clear_start_time = None  # interrupt clearing
            if self.confused_since is None:
                self.confused_since = now
            total = self.confused_elapsed + (now - self.confused_since)
            if total >= self.CONFUSED_THRESHOLD_SECONDS:
                self.is_confused = True

        elif emotion in NORMAL_EMOTIONS:
            # pause confused timer
            if self.confused_since is not None:
                self.confused_elapsed += now - self.confused_since
                self.confused_since = None

            if self.is_confused:
                # start/continue clear grace period
                if self.clear_start_time is None:
                    self.clear_start_time = now
                elif now - self.clear_start_time >= self.CLEAR_THRESHOLD_SECONDS:
                    # sustained normal — clear CONFUSED label
                    self.is_confused = False
                    self.clear_start_time = None
                    self.confused_elapsed = 0.0
                    self.recover_start_time = None
            else:
                # not confused — handle thinking timer recovery
                if self.recover_start_time is None:
                    self.recover_start_time = now
                elif now - self.recover_start_time >= self.RECOVER_GRACE_SECONDS:
                    self.confused_elapsed = 0.0
                    self.recover_start_time = None

        else:  # no face
            if self.confused_since is not None:
                self.confused_elapsed += now - self.confused_since
                self.confused_since = None
            self.clear_start_time = None  # interrupt clearing

        return self.is_confused

    def get_hud(self, emotion, confused):
        now = time.time()
        total = self.confused_elapsed
        if self.confused_since is not None:
            total += now - self.confused_since

        if emotion is None:
            return 'No face detected', (180, 180, 180)
        elif confused:
            if self.clear_start_time is not None:
                remaining = self.CLEAR_THRESHOLD_SECONDS - (now - self.clear_start_time)
                return f'CONFUSED (clearing in {remaining:.1f}s)', (0, 0, 255)
            return 'CONFUSED', (0, 0, 255)
        elif total > 0:
            remaining = self.CONFUSED_THRESHOLD_SECONDS - total
            return f'THINKING ({remaining:.1f}s left)', (0, 165, 255)
        else:
            return 'NORMAL', (0, 200, 80)
    
    def detect_confusion(self, frame_bgr):
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # only run heavy face detection every N frames
        if self._frame_count % self.DETECT_EVERY_N == 0:
            self._face_cache = self.detect_face(frame_rgb)
        self._frame_count += 1

        face = self._face_cache
        emotion = self.predict(face, frame_rgb)
        confused = self.check_focus(emotion)
        status_text, status_color = self.get_hud(emotion, confused)

        # cv2.putText(frame_bgr, status_text, (20, 40),
        #             cv2.FONT_HERSHEY_SIMPLEX, 1.0, status_color, 2)

        # if emotion is not None and face is not None:
        #     x1, y1, x2, y2 = [int(v) for v in face]
        #     cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), status_color, 2)
        #     cv2.putText(frame_bgr, emotion, (x1, y1 - 10),
        #                 cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

        return self.is_confused

    def run(self):
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FPS, 15)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        face = None
        frame_count = 0
        DETECT_EVERY_N = 3  # run face detection every 3 frames

        print(f'Running on: {DEVICE}')
        print('Press Q to quit')

        while True:
            ret, frame_bgr = cap.read()
            if not ret:
                break
            
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

            # if frame_count % DETECT_EVERY_N == 0:
            #     face = self.detect_face(frame_rgb)
            # frame_count += 1

            if self._frame_count % self.DETECT_EVERY_N == 0:
                self._face_cache = self.detect_face(frame_rgb)
            self._frame_count += 1
            face = self._face_cache


            emotion = self.predict(face, frame_rgb)
            confused = self.check_focus(emotion)
            status_text, status_color = self.get_hud(emotion, confused)

            cv2.putText(frame_bgr, status_text, (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, status_color, 2)

            if emotion is not None and face is not None:
                x1, y1, x2, y2 = [int(v) for v in face]
                cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), status_color, 2)
                cv2.putText(frame_bgr, emotion, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

            cv2.imshow('HSEmotion Inference [Q to quit]', frame_bgr)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    model_name = "enet_b0_8_best_vgaf"
    ConfuseDetector(model_name=model_name).run()