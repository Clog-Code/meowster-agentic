"""Helpers for constructing the language model used by the agent."""

import os

from langchain.chat_models import init_chat_model

from .config import LLM_DEFAULTS

# Parameters the OpenAI-compatible client accepts natively as top-level kwargs.
_OPENAI_STANDARD_PARAMS = {"temperature", "top_p", "presence_penalty", "max_tokens"}


def build_llm(
    base_url: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    mode_config: dict | None = None,
):
    """
    Build and return a LangChain chat model.

    Non-standard sampling params (top_k, min_p, repetition_penalty, etc.) are
    forwarded via `extra_body` so the client passes them as raw JSON body
    fields without validating them against the OpenAI SDK's known kwargs.
    """
    llm_base_url = base_url or os.getenv("LLM_BASE_URL")
    if not llm_base_url:
        raise RuntimeError("LLM_BASE_URL is not set. Copy .env.example to .env and fill it in.")

    resolved_temperature = (
        temperature if temperature is not None else float(LLM_DEFAULTS["temperature"])
    )

    standard_overrides: dict = {}
    extra_body: dict = {}

    if mode_config:
        for key, value in mode_config.items():
            if key == "temperature":
                resolved_temperature = value
            elif key in _OPENAI_STANDARD_PARAMS:
                standard_overrides[key] = value
            else:
                extra_body[key] = value

    return init_chat_model(
        model=model or os.getenv("LLM_MODEL"),
        model_provider="openai",
        base_url=llm_base_url,
        api_key=os.getenv("LLM_API_KEY"),
        temperature=resolved_temperature,
        stream_usage=True,
        max_tokens=int(LLM_DEFAULTS["max_tokens"]),
        extra_body=extra_body or None,
        **standard_overrides,
    )
