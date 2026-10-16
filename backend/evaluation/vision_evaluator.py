import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple


def calculate_iou(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
    """Calculate Intersection over Union of two bounding boxes (x1, y1, x2, y2)."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = max(0, boxA[2] - boxA[0]) * max(0, boxA[3] - boxA[1])
    boxBArea = max(0, boxB[2] - boxB[0]) * max(0, boxB[3] - boxB[1])

    denom = float(boxAArea + boxBArea - interArea)
    if denom <= 0:
        return 0.0
    return interArea / denom


@dataclass
class VisionFrameSample:
    frame_id: str
    image_data: Any
    has_face: bool
    gt_bbox: Optional[Tuple[int, int, int, int]] = None
    gt_emotion: Optional[str] = None
    gt_is_confused: bool = False
    gt_is_distracted: bool = False


@dataclass
class VisionEvaluationReport:
    total_frames: int
    face_detection_accuracy: float
    mean_iou: float
    emotion_accuracy: float
    confusion_fpr: float
    confusion_tpr: float
    avg_latency_ms: float
    throughput_fps: float
    confusion_matrix: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def summary(self) -> Dict[str, Any]:
        return {
            "total_frames": self.total_frames,
            "face_detection_accuracy": round(self.face_detection_accuracy, 4),
            "mean_iou": round(self.mean_iou, 4),
            "emotion_accuracy": round(self.emotion_accuracy, 4),
            "confusion_fpr": round(self.confusion_fpr, 4),
            "confusion_tpr": round(self.confusion_tpr, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "throughput_fps": round(self.throughput_fps, 2),
        }


class VisionEvaluator:
    """Quantitative evaluation suite for Vision face detection, emotion, and confusion analysis."""

    def __init__(self, detector_engine=None):
        self.detector_engine = detector_engine

    def evaluate(self, samples: List[VisionFrameSample], predict_fn=None) -> VisionEvaluationReport:
        if not samples:
            return VisionEvaluationReport(
                total_frames=0,
                face_detection_accuracy=0.0,
                mean_iou=0.0,
                emotion_accuracy=0.0,
                confusion_fpr=0.0,
                confusion_tpr=0.0,
                avg_latency_ms=0.0,
                throughput_fps=0.0,
            )

        correct_face_detections = 0
        iou_scores = []
        emotion_matches = 0
        emotion_eval_count = 0
        false_confusion_count = 0
        true_confusion_negatives = 0
        true_confusion_positives = 0
        total_confusion_positives = 0
        latencies = []

        confusion_matrix: Dict[str, Dict[str, int]] = {}

        for sample in samples:
            t0 = time.perf_counter()
            if predict_fn:
                pred = predict_fn(sample.image_data)
            elif self.detector_engine:
                pred = self.detector_engine.detect(sample.image_data)
            else:
                pred = {"face": None, "emotion": None, "confused": False, "distracted": False}
            elapsed_ms = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed_ms)

            pred_face = pred.get("face")
            pred_emotion = pred.get("emotion")
            pred_confused = bool(pred.get("confused"))

            # 1. Face detection accuracy
            face_detected = pred_face is not None
            if face_detected == sample.has_face:
                correct_face_detections += 1

            if sample.has_face and sample.gt_bbox and pred_face:
                iou = calculate_iou(tuple(pred_face), sample.gt_bbox)
                iou_scores.append(iou)

            # 2. Emotion classification accuracy & confusion matrix
            if sample.gt_emotion:
                emotion_eval_count += 1
                gt_em = sample.gt_emotion.lower()
                pr_em = (pred_emotion or "unknown").lower()

                if gt_em not in confusion_matrix:
                    confusion_matrix[gt_em] = {}
                confusion_matrix[gt_em][pr_em] = confusion_matrix[gt_em].get(pr_em, 0) + 1

                if gt_em == pr_em:
                    emotion_matches += 1

            # 3. Confusion FPR and TPR
            if not sample.gt_is_confused:
                true_confusion_negatives += 1
                if pred_confused:
                    false_confusion_count += 1
            else:
                total_confusion_positives += 1
                if pred_confused:
                    true_confusion_positives += 1

        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
        fps = (1000.0 / avg_lat) if avg_lat > 0 else 0.0

        return VisionEvaluationReport(
            total_frames=len(samples),
            face_detection_accuracy=correct_face_detections / len(samples),
            mean_iou=sum(iou_scores) / len(iou_scores) if iou_scores else 0.0,
            emotion_accuracy=emotion_matches / emotion_eval_count if emotion_eval_count else 0.0,
            confusion_fpr=false_confusion_count / true_confusion_negatives if true_confusion_negatives else 0.0,
            confusion_tpr=true_confusion_positives / total_confusion_positives if total_confusion_positives else 0.0,
            avg_latency_ms=avg_lat,
            throughput_fps=fps,
            confusion_matrix=confusion_matrix,
        )
