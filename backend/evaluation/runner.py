import json
import logging
from typing import Dict, Any

from evaluation.rag_evaluator import RAGEvaluator, RAGTestCase
from evaluation.vision_evaluator import VisionEvaluator, VisionFrameSample

logger = logging.getLogger(__name__)


def create_sample_rag_benchmark() -> list[RAGTestCase]:
    """Curated golden test dataset for RAG retrieval across multiple tenant partitions."""
    return [
        RAGTestCase(
            query="What is Newton's second law of motion?",
            tenant_id="user_alice",
            expected_sources=["physics_mechanics.pdf"],
            expected_keywords=["F = ma", "force", "mass", "acceleration"],
        ),
        RAGTestCase(
            query="Explain the process of photosynthesis",
            tenant_id="user_alice",
            expected_sources=["biology_plants.pdf"],
            expected_keywords=["chloroplast", "glucose", "light reaction"],
        ),
        RAGTestCase(
            query="How does gradient descent optimization work?",
            tenant_id="user_bob",
            expected_sources=["machine_learning_foundations.pdf"],
            expected_keywords=["learning rate", "loss function", "derivative"],
        ),
        # Cross-tenant isolation probe: Alice attempts to query Bob's ML documents
        RAGTestCase(
            query="What is the learning rate in gradient descent?",
            tenant_id="user_alice",
            expected_sources=["machine_learning_foundations.pdf"],
            cross_tenant_probe=True,
        ),
    ]


def create_sample_vision_benchmark() -> list[VisionFrameSample]:
    """Synthetic/curated test cases for vision face detection and emotion classification."""
    return [
        VisionFrameSample(
            frame_id="frame_01_neutral",
            image_data="sample_neutral_frame",
            has_face=True,
            gt_bbox=(50, 50, 200, 200),
            gt_emotion="neutral",
            gt_is_confused=False,
        ),
        VisionFrameSample(
            frame_id="frame_02_happiness",
            image_data="sample_happy_frame",
            has_face=True,
            gt_bbox=(60, 60, 210, 210),
            gt_emotion="happiness",
            gt_is_confused=False,
        ),
        VisionFrameSample(
            frame_id="frame_03_surprise_confused",
            image_data="sample_surprise_frame",
            has_face=True,
            gt_bbox=(55, 55, 205, 205),
            gt_emotion="surprise",
            gt_is_confused=True,
        ),
        VisionFrameSample(
            frame_id="frame_04_no_face",
            image_data="sample_background_frame",
            has_face=False,
            gt_bbox=None,
            gt_emotion=None,
            gt_is_confused=False,
        ),
    ]


def run_all_benchmarks() -> Dict[str, Any]:
    # 1. RAG Benchmark
    rag_test_cases = create_sample_rag_benchmark()

    # Mock retriever function for benchmark demonstration
    def mock_retriever(query: str, user_id: str, n_results: int = 5):
        # Alice only has access to physics and biology
        if user_id == "user_alice":
            if "newton" in query.lower():
                return {"results": [{"metadata": {"source": "physics_mechanics.pdf", "user_id": "user_alice"}}]}
            if "photosynthesis" in query.lower():
                return {"results": [{"metadata": {"source": "biology_plants.pdf", "user_id": "user_alice"}}]}
            return {"results": []}
        if user_id == "user_bob":
            if "gradient" in query.lower():
                return {"results": [{"metadata": {"source": "machine_learning_foundations.pdf", "user_id": "user_bob"}}]}
        return {"results": []}

    rag_evaluator = RAGEvaluator(retriever_fn=mock_retriever)
    rag_report = rag_evaluator.evaluate(rag_test_cases)

    # 2. Vision Benchmark
    vision_test_cases = create_sample_vision_benchmark()

    def mock_vision_predictor(img_data: str):
        if "background" in img_data:
            return {"face": None, "emotion": None, "confused": False}
        if "neutral" in img_data:
            return {"face": (52, 51, 198, 201), "emotion": "neutral", "confused": False}
        if "happy" in img_data:
            return {"face": (60, 60, 210, 210), "emotion": "happiness", "confused": False}
        if "surprise" in img_data:
            return {"face": (55, 55, 205, 205), "emotion": "surprise", "confused": True}
        return {"face": None, "emotion": None, "confused": False}

    vision_evaluator = VisionEvaluator()
    vision_report = vision_evaluator.evaluate(vision_test_cases, predict_fn=mock_vision_predictor)

    results = {
        "rag": rag_report.summary(),
        "vision": vision_report.summary(),
    }

    return results


if __name__ == "__main__":
    benchmark_results = run_all_benchmarks()
    print("=" * 60)
    print("           MINDFLOW QUANTITATIVE BENCHMARK REPORT           ")
    print("=" * 60)
    print(json.dumps(benchmark_results, indent=2))
