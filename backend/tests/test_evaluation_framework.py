from evaluation.rag_evaluator import RAGEvaluator, RAGTestCase
from evaluation.vision_evaluator import VisionEvaluator, VisionFrameSample, calculate_iou
from evaluation.runner import run_all_benchmarks


def test_calculate_iou():
    box1 = (0, 0, 10, 10)  # Area 100
    box2 = (0, 0, 10, 10)  # Area 100 -> Perfect match
    assert calculate_iou(box1, box2) == 1.0

    box3 = (10, 10, 20, 20)  # No overlap
    assert calculate_iou(box1, box3) == 0.0

    box4 = (5, 0, 15, 10)  # 50% overlap
    iou = calculate_iou(box1, box4)
    assert round(iou, 2) == 0.33


def test_rag_evaluator_metrics():
    test_cases = [
        RAGTestCase(
            query="test q1",
            tenant_id="tenant_a",
            expected_sources=["doc_1.pdf"],
        ),
        RAGTestCase(
            query="test q2",
            tenant_id="tenant_a",
            expected_sources=["doc_2.pdf"],
        ),
        # Cross tenant probe: should NOT return foreign doc
        RAGTestCase(
            query="test probe",
            tenant_id="tenant_a",
            expected_sources=["secret.pdf"],
            cross_tenant_probe=True,
        ),
    ]

    def mock_retriever(query, user_id, n_results=5):
        if "q1" in query:
            return {"results": [{"metadata": {"source": "doc_1.pdf", "user_id": user_id}}]}
        if "q2" in query:
            # Match is at position 2 (rank 2)
            return {
                "results": [
                    {"metadata": {"source": "unrelated.pdf", "user_id": user_id}},
                    {"metadata": {"source": "doc_2.pdf", "user_id": user_id}},
                ]
            }
        return {"results": []}

    evaluator = RAGEvaluator(retriever_fn=mock_retriever)
    report = evaluator.evaluate(test_cases)

    assert report.total_queries == 3
    assert report.hit_rate_at_3 == 1.0  # Both queries found in top 3
    assert report.mrr == (1.0 + 0.5) / 2.0  # 0.75
    assert report.tenant_leak_count == 0
    assert report.tenant_leak_rate == 0.0


def test_vision_evaluator_metrics():
    samples = [
        VisionFrameSample(
            frame_id="f1",
            image_data="data1",
            has_face=True,
            gt_bbox=(10, 10, 50, 50),
            gt_emotion="happiness",
            gt_is_confused=False,
        ),
        VisionFrameSample(
            frame_id="f2",
            image_data="data2",
            has_face=False,
            gt_bbox=None,
            gt_emotion=None,
            gt_is_confused=False,
        ),
        VisionFrameSample(
            frame_id="f3",
            image_data="data3",
            has_face=True,
            gt_bbox=(20, 20, 60, 60),
            gt_emotion="sadness",
            gt_is_confused=True,
        ),
    ]

    def mock_predict(img):
        if img == "data1":
            return {"face": (10, 10, 50, 50), "emotion": "happiness", "confused": False}
        if img == "data2":
            return {"face": None, "emotion": None, "confused": False}
        if img == "data3":
            return {"face": (20, 20, 60, 60), "emotion": "sadness", "confused": True}
        return {}

    evaluator = VisionEvaluator()
    report = evaluator.evaluate(samples, predict_fn=mock_predict)

    assert report.total_frames == 3
    assert report.face_detection_accuracy == 1.0
    assert report.mean_iou == 1.0
    assert report.emotion_accuracy == 1.0
    assert report.confusion_fpr == 0.0
    assert report.confusion_tpr == 1.0


def test_run_all_benchmarks_generates_valid_report():
    results = run_all_benchmarks()
    assert "rag" in results
    assert "vision" in results
    assert results["rag"]["hit_rate@3"] >= 0.0
    assert results["vision"]["face_detection_accuracy"] >= 0.0
