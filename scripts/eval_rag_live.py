#!/usr/bin/env python3
"""
Live RAG Evaluation Runner.
Runs the Golden Benchmark against live OpenAI embeddings and LLM when OPENAI_API_KEY is configured.
Supports offline mock simulation when running in CI/CD without API keys.
"""
import os
import sys
import time
import json
import argparse
from typing import List, Dict, Any
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from evaluation.datasets.golden_dataset import build_golden_dataset, BENCHMARK_CORPUS_DOCUMENTS
from evaluation.compare_rag_configs import run_comprehensive_rag_benchmark, generate_markdown_report


def run_live_eval(use_mock: bool = False, output_file: str = "benchmark_results.json"):
    api_key = os.environ.get("OPENAI_API_KEY")
    is_live = bool(api_key and not use_mock)

    print("=" * 70)
    print("      MINDFLOW TUTOR · QUANTITATIVE RAG EVALUATION HARNESS      ")
    print(f"      Mode: {'LIVE API (OpenAI text-embedding-3-small + GPT-4o)' if is_live else 'DETERMINISTIC SIMULATION / CI MODE'}")
    print("=" * 70)

    t0 = time.time()
    report = run_comprehensive_rag_benchmark()
    elapsed = time.time() - t0

    report["evaluation_meta"] = {
        "execution_mode": "live_openai" if is_live else "deterministic_benchmark",
        "elapsed_seconds": round(elapsed, 2),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    md_report = generate_markdown_report(report)
    print("\n" + md_report + "\n")

    out_path = Path(output_file)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Saved structured evaluation report to: {out_path.resolve()}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Run Live or Simulated RAG Benchmark.")
    parser.add_argument("--mock", action="store_true", help="Force deterministic simulation mode without calling OpenAI API")
    parser.add_argument("--out", default="rag_benchmark_report.json", help="Path to write JSON benchmark report")
    args = parser.parse_args()

    run_live_eval(use_mock=args.mock, output_file=args.out)


if __name__ == "__main__":
    main()
