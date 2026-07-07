"""Helpers for constructing the language model used by the agent — Fireworks AI."""

import os

from langchain.chat_models import init_chat_model

from .config import LLM_DEFAULTS

# Fireworks-native params that ChatFireworks accepts as top-level kwargs.
# Anything else (top_k, min_p, repetition_penalty, etc.) gets routed into
# model_kwargs, which ChatFireworks forwards as raw request-body fields.
_FIREWORKS_STANDARD_PARAMS = {"temperature", "max_tokens", "stop"}


def build_llm(
    model: str | None = None,
    temperature: float | None = None,
    mode_config: dict | None = None,
):
    """
    Build and return a LangChain chat model backed by Fireworks AI.

    `model` should be a full Fireworks model id, e.g.
    "accounts/fireworks/models/qwen3p7-plus" (see FIREWORKS_MODEL in .env).
    We pass it to `init_chat_model` with the "fireworks:" provider prefix,
    matching deepagents' own `model="fireworks:accounts/..."` shorthand.

    Non-standard sampling params (top_k, min_p, repetition_penalty, etc.) are
    forwarded via `model_kwargs` so they reach the raw Fireworks request body
    without being validated against ChatFireworks' known constructor kwargs.
    """
    fireworks_model = model or os.getenv("FIREWORKS_MODEL") or os.getenv("LLM_MODEL")
    if not fireworks_model:
        raise RuntimeError(
            "FIREWORKS_MODEL is not set. Copy .env.example to .env and fill it in "
            "with a Fireworks model id, e.g. accounts/fireworks/models/qwen3p7-plus"
        )

    api_key = os.getenv("FIREWORKS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "FIREWORKS_API_KEY is not set. Copy .env.example to .env and fill it in "
            "with your Fireworks AI API key."
        )

    # Start with defaults, then let mode_config override anything it specifies.
    resolved: dict = {
        "temperature": temperature if temperature is not None else float(LLM_DEFAULTS["temperature"]),
        "max_tokens": int(LLM_DEFAULTS["max_tokens"]),
    }
    model_kwargs: dict = {}

    if mode_config:
        for key, value in mode_config.items():
            if key in _FIREWORKS_STANDARD_PARAMS:
                resolved[key] = value
            else:
                model_kwargs[key] = value

    # Prefixing with "fireworks:" tells init_chat_model to build a
    # ChatFireworks instance (requires langchain-fireworks to be installed).
    call_kwargs: dict = {
        "model": f"fireworks:{fireworks_model}",
        "api_key": api_key,
        "stream_usage": True,
        **resolved,
    }
    if model_kwargs:
        call_kwargs["model_kwargs"] = model_kwargs

    return init_chat_model(**call_kwargs)