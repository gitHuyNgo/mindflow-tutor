from engines.confusion_system.confusion_calibrator import ConfusionCalibrator
from evaluation.confusion_reliability import evaluate_confusion_reliability


def test_instantaneous_confusion_scoring():
    calibrator = ConfusionCalibrator()

    # Happiness is an inhibitor -> 0.0 confusion
    score_happy = calibrator.compute_instantaneous_score("happiness")
    assert score_happy == 0.0

    # Neutral has negligible confusion
    score_neutral = calibrator.compute_instantaneous_score("neutral")
    assert score_neutral <= 0.1

    # Anger / surprise indicate cognitive challenge
    score_anger = calibrator.compute_instantaneous_score("anger")
    score_surprise = calibrator.compute_instantaneous_score("surprise")
    assert score_anger >= 0.35
    assert score_surprise >= 0.40

    # Distribution with high happiness suppresses confusion
    dist = {"happiness": 0.8, "anger": 0.2}
    score_dist = calibrator.compute_instantaneous_score(None, dist)
    assert score_dist == 0.0


def test_calibrator_suppresses_transient_frowns():
    calibrator = ConfusionCalibrator(sensitivity="medium")
    is_confused = False
    smoothed = 0.0
    confused_since = None

    # Simulate 5 frames of brief frown (0.5s at 10 fps)
    for i in range(5):
        is_confused, smoothed, confused_since, _ = calibrator.update(
            current_smoothed=smoothed,
            is_currently_confused=is_confused,
            top_emotion="anger",
            confused_since=confused_since,
            now=i * 0.1,
        )

    # Must NOT trigger confusion on brief micro-expression
    assert is_confused is False


def test_calibrator_triggers_on_sustained_confusion():
    calibrator = ConfusionCalibrator(sensitivity="medium")
    is_confused = False
    smoothed = 0.0
    confused_since = None

    # Simulate 50 frames (5.0s) of sustained confusion
    for i in range(50):
        is_confused, smoothed, confused_since, _ = calibrator.update(
            current_smoothed=smoothed,
            is_currently_confused=is_confused,
            top_emotion="surprise",
            confused_since=confused_since,
            now=i * 0.1,
        )

    # Must trigger confusion after sustained period
    assert is_confused is True
    assert smoothed >= 0.40


def test_sensitivity_profiles():
    low_calib = ConfusionCalibrator(sensitivity="low")
    high_calib = ConfusionCalibrator(sensitivity="high")

    assert low_calib.config["trigger_threshold"] > high_calib.config["trigger_threshold"]
    assert low_calib.config["min_sustained_seconds"] > high_calib.config["min_sustained_seconds"]


def test_confusion_reliability_evaluation():
    report = evaluate_confusion_reliability()
    assert "calibrated_model" in report
    assert "legacy_uncalibrated" in report
    # Calibrated FPR must be lower or equal to legacy
    assert report["calibrated_model"]["false_positive_rate"] <= report["legacy_uncalibrated"]["false_positive_rate"]
