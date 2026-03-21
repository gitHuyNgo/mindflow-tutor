import cv2

from engines.attention_system.DistractDetector import DistractionDetector
from engines.confusion_system.noptConfuseDetector import ConfuseDetector


def main():
    confuse_detector = ConfuseDetector(confuse_threshold=5, recover_threshold=3, clear_threshold=1)
    distract_detector = DistractionDetector()

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FPS, 15)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("Press Q to quit")

    while True:
        ret, frame_bgr = cap.read()
        if not ret:
            break

        distracted, is_centered = distract_detector.detect_distraction(frame_bgr)

        confused = False
        if is_centered:
            confused = confuse_detector.detect_confusion(frame_bgr)

        if confused:
            print("CONFUSED!")
        if distracted:
            print("DISTRACTED!")

        cv2.imshow("Confusion and Distraction [Q to quit]", frame_bgr)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
