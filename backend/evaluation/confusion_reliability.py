"""
Reliability and False-Positive Rate (FPR) Evaluation for Emotion-Based Confusion Inference.
Compares the uncalibrated binary heuristic vs the calibrated multi-signal model.
"""
from typing import List, Dict, Any, Tuple
from engines.confusion_system.confusion_calibrator import ConfusionCalibrator, DEFAULT_EMOTION_CONFUSION_WEIGHTS


def evaluate_confusion_reliability() -> Dict[str, Any]:
    """
    Run simulated longitudinal emotion streams representing common learner behaviors:
    1. deep_focus: Learner squints/furrows brow reading complex text (anger/contempt/neutral)
    2. transient_grimace: A 0.5-second brief squint/yawn
    3. genuine_confusion: Sustained surprise and frustration
    4. happy_flow: Engaged, smiling learner
    """
    calibrator = ConfusionCalibrator(sensitivity="medium")

    # Frame rate: 10 FPS
    fps = 10.0
    dt = 1.0 / fps

    def run_simulation(scenario: List[str], use_calibrated: bool) -> Tuple[int, int, List[bool]]:
        # Returns: (total_frames, confused_frames, timeline)
        is_confused = False
        smoothed = 0.0
        confused_since = None
        timeline = []

        # Legacy binary tracking variables
        legacy_elapsed = 0.0
        legacy_confused_since = None

        now = 0.0
        for emotion in scenario:
            now += dt
            if use_calibrated:
                is_confused, smoothed, confused_since, _ = calibrator.update(
                    current_smoothed=smoothed,
                    is_currently_confused=is_confused,
                    top_emotion=emotion,
                    confused_since=confused_since,
                    now=now,
                )
            else:
                # Legacy uncalibrated logic:
                if emotion in {"sadness", "anger", "disgust", "fear", "contempt"}:
                    if legacy_confused_since is None:
                        legacy_confused_since = now
                    legacy_elapsed += dt
                    if legacy_elapsed >= 3.0:
                        is_confused = True
                elif emotion in {"neutral", "happiness", "surprise"}:
                    legacy_confused_since = None
                    if is_confused:
                        legacy_elapsed = 0.0
                        is_confused = False
                timeline.append(is_confused)
            timeline.append(is_confused)

        return len(scenario), sum(1 for x in timeline if x), timeline

    # 1. Deep focus scenario: 6 seconds of deep reading (neutral with intermittent frowns)
    # A concentrated reader often shows neutral mixed with brief anger/contempt
    deep_focus = ["neutral"] * 15 + ["anger"] * 10 + ["neutral"] * 15 + ["contempt"] * 10 + ["neutral"] * 10

    # 2. Transient grimace: 0.5 seconds of sadness followed by neutral
    transient_grimace = ["neutral"] * 20 + ["sadness"] * 5 + ["neutral"] * 25

    # 3. Genuine confusion: 5 seconds of sustained surprise and frustration
    genuine_confusion = ["surprise"] * 20 + ["anger"] * 30 + ["fear"] * 10

    # Evaluate legacy
    _, legacy_df_confused, _ = run_simulation(deep_focus, use_calibrated=False)
    _, legacy_tg_confused, _ = run_simulation(transient_grimace, use_calibrated=False)
    _, legacy_gc_confused, _ = run_simulation(genuine_confusion, use_calibrated=False)

    # Evaluate calibrated
    _, calib_df_confused, _ = run_simulation(deep_focus, use_calibrated=True)
    _, calib_tg_confused, _ = run_simulation(transient_grimace, use_calibrated=True)
    _, calib_gc_confused, _ = run_simulation(genuine_confusion, use_calibrated=True)

    fpr_legacy = (legacy_df_confused + legacy_tg_confused) / (len(deep_focus) + len(transient_grimace))
    fpr_calib = (calib_df_confused + calib_tg_confused) / (len(deep_focus) + len(transient_grimace))

    tpr_legacy = 1.0 if legacy_gc_confused > 0 else 0.0
    tpr_calib = 1.0 if calib_gc_confused > 0 else 0.0

    fpr_reduction = ((fpr_legacy - fpr_calib) / fpr_legacy * 100.0) if fpr_legacy > 0 else 0.0

    report = {
        "legacy_uncalibrated": {
            "deep_focus_false_triggers": legacy_df_confused > 0,
            "transient_grimace_false_triggers": legacy_tg_confused > 0,
            "genuine_confusion_detected": legacy_gc_confused > 0,
            "false_positive_rate": round(fpr_legacy, 4),
            "true_positive_rate": round(tpr_legacy, 4),
        },
        "calibrated_model": {
            "deep_focus_false_triggers": calib_df_confused > 0,
            "transient_grimace_false_triggers": calib_tg_confused > 0,
            "genuine_confusion_detected": calib_gc_confused > 0,
            "false_positive_rate": round(fpr_calib, 4),
            "true_positive_rate": round(tpr_calib, 4),
        },
        "evaluation_summary": {
            "fpr_reduction_pct": round(fpr_reduction, 2),
            "recommendation": "Use calibrated multi-signal scoring with temporal EMA to prevent interrupting deep reading",
        },
    }

    return report


if __name__ == "__main__":
    import json
    print(json.dumps(evaluate_confusion_reliability(), indent=2))
