from evaluation.confusion_action_units import (
    ActionUnitFrame,
    ActionUnitConfusionModel,
    evaluate_action_unit_framework,
)


def test_action_unit_reading_squint_suppression():
    model = ActionUnitConfusionModel()

    # Reading frame: high brow furrow (AU4) and squint (AU7), but looking straight ahead with active scroll
    reading_frame = ActionUnitFrame(
        frame_index=1,
        timestamp_s=0.1,
        au4_brow_lowerer=0.75,
        au7_lid_tightener=0.70,
        au12_lip_corner_puller=0.0,
        head_tilt_deg=1.5,
        gaze_fixation_s=0.3,
        has_interaction=True,
        ground_truth_confused=False,
    )

    instant_score = model.compute_instantaneous_index(reading_frame)
    # Instantaneous score must be suppressed below 0.35 because of reading squint discount and active interaction
    assert instant_score < 0.35

    is_confused, smoothed = model.update(reading_frame)
    assert is_confused is False


def test_action_unit_genuine_confusion_trigger():
    model = ActionUnitConfusionModel()

    # Stagnant gaze, head tilted sideways, no keyboard/mouse interaction
    confused_frame = ActionUnitFrame(
        frame_index=25,
        timestamp_s=2.5,
        au4_brow_lowerer=0.85,
        au7_lid_tightener=0.10,
        au12_lip_corner_puller=0.0,
        head_tilt_deg=14.0,
        gaze_fixation_s=3.5,
        has_interaction=False,
        ground_truth_confused=True,
    )

    instant_score = model.compute_instantaneous_index(confused_frame)
    assert instant_score >= 0.70


def test_action_unit_smile_inhibitor():
    model = ActionUnitConfusionModel()

    # Frame with brow furrow but also smiling (AU12) -> amused/pleased, not confused
    happy_frame = ActionUnitFrame(
        frame_index=1,
        timestamp_s=0.1,
        au4_brow_lowerer=0.50,
        au7_lid_tightener=0.10,
        au12_lip_corner_puller=0.60,
        head_tilt_deg=0.0,
        gaze_fixation_s=0.5,
        has_interaction=True,
        ground_truth_confused=False,
    )

    instant_score = model.compute_instantaneous_index(happy_frame)
    assert instant_score == 0.0


def test_action_unit_cohort_benchmark():
    benchmark_report = evaluate_action_unit_framework()
    metrics = benchmark_report["metrics"]

    # Multi-modal AU calibrated model should have significantly lower FPR than naive detector
    assert metrics["multimodal_au_calibrated_fpr"] < metrics["naive_single_frame_fpr"]
    assert metrics["fpr_reduction_pct"] > 80.0
    assert metrics["true_positive_rate"] >= 0.90
