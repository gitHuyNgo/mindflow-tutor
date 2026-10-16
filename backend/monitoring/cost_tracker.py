import threading
from typing import Dict, Any, Optional

# Current public pricing per unit (USD)
# Source: OpenAI & LlamaIndex pricing tables (2025/2026)
PRICING_TABLE = {
    "gpt-4o-mini": {
        "input_per_million": 0.150,
        "output_per_million": 0.600,
    },
    "gpt-4o": {
        "input_per_million": 2.500,
        "output_per_million": 10.000,
    },
    "text-embedding-3-small": {
        "input_per_million": 0.020,
    },
    "openai-tts": {
        "per_million_chars": 15.000,
    },
    "llama-parse": {
        "per_page": 0.003,
    },
}

_cost_lock = threading.Lock()


class CostTracker:
    """Tracks token, embedding, audio, and parsing costs across tutoring workflows."""

    def __init__(self):
        self.usage_records = {
            "llm_prompt_tokens": {},
            "llm_completion_tokens": {},
            "embedding_tokens": 0,
            "tts_characters": 0,
            "parsed_pages": 0,
        }

    def record_llm(self, model: str, prompt_tokens: int, completion_tokens: int):
        with _cost_lock:
            self.usage_records["llm_prompt_tokens"][model] = (
                self.usage_records["llm_prompt_tokens"].get(model, 0) + prompt_tokens
            )
            self.usage_records["llm_completion_tokens"][model] = (
                self.usage_records["llm_completion_tokens"].get(model, 0) + completion_tokens
            )

    def record_embedding(self, tokens: int):
        with _cost_lock:
            self.usage_records["embedding_tokens"] += tokens

    def record_tts(self, characters: int):
        with _cost_lock:
            self.usage_records["tts_characters"] += characters

    def record_parsing(self, pages: int):
        with _cost_lock:
            self.usage_records["parsed_pages"] += pages

    def calculate_total_cost_usd(self) -> float:
        total = 0.0
        with _cost_lock:
            # LLM costs
            for model, p_tokens in self.usage_records["llm_prompt_tokens"].items():
                p_rate = PRICING_TABLE.get(model, PRICING_TABLE["gpt-4o-mini"])["input_per_million"]
                total += (p_tokens / 1_000_000.0) * p_rate

            for model, c_tokens in self.usage_records["llm_completion_tokens"].items():
                c_rate = PRICING_TABLE.get(model, PRICING_TABLE["gpt-4o-mini"])["output_per_million"]
                total += (c_tokens / 1_000_000.0) * c_rate

            # Embedding
            emb_rate = PRICING_TABLE["text-embedding-3-small"]["input_per_million"]
            total += (self.usage_records["embedding_tokens"] / 1_000_000.0) * emb_rate

            # TTS
            tts_rate = PRICING_TABLE["openai-tts"]["per_million_chars"]
            total += (self.usage_records["tts_characters"] / 1_000_000.0) * tts_rate

            # Parser
            parse_rate = PRICING_TABLE["llama-parse"]["per_page"]
            total += self.usage_records["parsed_pages"] * parse_rate

        return total

    @staticmethod
    def estimate_session_cost(
        turns: int = 15,
        avg_prompt_tokens: int = 500,
        avg_completion_tokens: int = 250,
        tts_chars_per_turn: int = 400,
        rag_doc_pages: int = 10,
        model: str = "gpt-4o-mini",
    ) -> Dict[str, Any]:
        """
        Estimate the total cost for a typical 30-minute student study session.
        """
        total_prompt_tokens = turns * avg_prompt_tokens
        total_completion_tokens = turns * avg_completion_tokens
        total_tts_chars = turns * tts_chars_per_turn

        pricing = PRICING_TABLE.get(model, PRICING_TABLE["gpt-4o-mini"])
        llm_prompt_cost = (total_prompt_tokens / 1_000_000.0) * pricing["input_per_million"]
        llm_completion_cost = (total_completion_tokens / 1_000_000.0) * pricing["output_per_million"]
        tts_cost = (total_tts_chars / 1_000_000.0) * PRICING_TABLE["openai-tts"]["per_million_chars"]
        rag_cost = rag_doc_pages * PRICING_TABLE["llama-parse"]["per_page"]

        session_cost_usd = llm_prompt_cost + llm_completion_cost + tts_cost + rag_cost

        return {
            "model": model,
            "turns": turns,
            "llm_prompt_cost_usd": round(llm_prompt_cost, 6),
            "llm_completion_cost_usd": round(llm_completion_cost, 6),
            "tts_cost_usd": round(tts_cost, 6),
            "rag_indexing_cost_usd": round(rag_cost, 6),
            "total_session_cost_usd": round(session_cost_usd, 6),
            "cost_per_100_sessions_usd": round(session_cost_usd * 100, 3),
            "cost_per_1000_sessions_usd": round(session_cost_usd * 1000, 2),
        }

    def generate_report(self) -> Dict[str, Any]:
        total_cost = self.calculate_total_cost_usd()
        benchmark = self.estimate_session_cost()
        return {
            "current_run_usage": dict(self.usage_records),
            "current_run_total_cost_usd": round(total_cost, 6),
            "projected_session_benchmark": benchmark,
        }


# Singleton instance
_cost_tracker = CostTracker()


def get_cost_tracker() -> CostTracker:
    return _cost_tracker


if __name__ == "__main__":
    import json
    tracker = CostTracker()
    tracker.record_llm("gpt-4o-mini", 50000, 20000)
    tracker.record_embedding(15000)
    tracker.record_tts(10000)
    tracker.record_parsing(5)
    print(json.dumps(tracker.generate_report(), indent=2))
