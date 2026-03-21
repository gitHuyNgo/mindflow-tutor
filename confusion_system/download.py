import urllib.request
from pathlib import Path


PROTOTXT_URL = "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt"
WEIGHTS_URL = "https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"
PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_DIR = PROJECT_ROOT / "model"
PROTOTXT_PATH = MODEL_DIR / "deploy.prototxt"
WEIGHTS_PATH = MODEL_DIR / "res10_300x300_ssd.caffemodel"


def download_dnn_model():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    if not PROTOTXT_PATH.exists():
        print("Downloading face detector prototxt...")
        urllib.request.urlretrieve(PROTOTXT_URL, PROTOTXT_PATH)
    if not WEIGHTS_PATH.exists():
        print("Downloading face detector weights...")
        urllib.request.urlretrieve(WEIGHTS_URL, WEIGHTS_PATH)


if __name__ == "__main__":
    download_dnn_model()