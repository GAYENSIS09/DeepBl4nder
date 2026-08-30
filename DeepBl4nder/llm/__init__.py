"""LLM local routing via llama-cpp-python server.

Provides task-based model selection with cascade escalation:
Qwen3-1.5B (fast) → Qwen3-4B (general) → Qwen3-8B (coding/reasoning).
"""

from DeepBl4nder.llm.interface import (
    LLMClient,
    build_llm,
    get_router,
    last_attempt,
    last_decision,
    model_name_of,
    reset_router,
    routing_stats,
)

__all__ = [
    "LLMClient",
    "build_llm",
    "get_router",
    "last_attempt",
    "last_decision",
    "model_name_of",
    "reset_router",
    "routing_stats",
]
