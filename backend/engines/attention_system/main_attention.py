import cv2
import time

from camera.webcam import WebcamStream
from vision.face_detector import FaceDetector
from vision.head_pose import HeadPoseEstimator

from attention.attention_tracker import AttentionTracker
from attention.distraction_detector import DistractionDetector

from agent.reminder_agent import ReminderAgent


def main():

    camera = WebcamStream()

    face_detector = FaceDetector()

    head_pose = HeadPoseEstimator()

    eye_tracker = AttentionTracker()

    distraction = DistractionDetector()

    agent = ReminderAgent()

    while True:

        frame = camera.read()

        if frame is None:
            break

        landmarks = face_detector.detect(frame)

        distracted = False

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

            cv2.putText(
                frame,
                f"Away: {away_time:.1f}s",
                (20, 120),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2
            )

            cv2.putText(frame, f"Head: {head_dir}",
                        (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 255, 0), 2)

            cv2.putText(frame, f"Eye: {eye_dir}",
                        (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 255, 0), 2)

        notify = distraction.update(distracted)

        if notify:
            agent.remind()

        cv2.imshow("Attention Monitor", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
