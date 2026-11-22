"""Deployment-owned provider configuration. No credentials are read on import."""
import math
import os

MODELS = {"groq": "GROQ_MODEL", "gemini": "GEMINI_MODEL", "openrouter": "OPENROUTER_MODEL"}
KEYS = {"groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
FREE_MODELS = frozenset({"qwen/qwen3-coder:free", "meta-llama/llama-3.3-70b-instruct:free"})


def model_for(provider, override=None):
    return override or os.getenv(MODELS.get(provider, ""), "").strip() or (
        "openai/gpt-oss-120b" if provider == "groq" else ""
    )


def timeout_for(provider):
    timeout = float(os.getenv(f"{provider.upper()}_TIMEOUT_SECONDS", "30"))
    if not math.isfinite(timeout) or not 0 < timeout <= 120:
        raise ValueError("Invalid provider timeout.")
    return timeout



def enabled(provider):
    return provider in {value.strip() for value in os.getenv("LLM_ENABLED_PROVIDERS", "groq").split(",")}



def provider_order(primary, *, allow_fallback, override=None):
    if not allow_fallback:
        return (primary,)
    order = override if override is not None else os.getenv("LLM_PROVIDER_ORDER", "groq,gemini,openrouter").split(",")
    order = tuple(item.strip() for item in order)
    if not order or len(order) > len(KEYS) or len(set(order)) != len(order) or any(item not in KEYS for item in order):
        raise ValueError("Invalid provider priority.")
    return order


def configured(provider, model, api_key=None):
    if not enabled(provider) or not model:
        return False
    key = api_key if provider == "groq" and api_key is not None else os.getenv(KEYS[provider], "")
    if not key.strip() or (provider == "openrouter" and model not in FREE_MODELS):
        return False
    if provider == "gemini":
        import re
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}", model):
            return False
    try:
        timeout_for(provider)
    except ValueError:
        return False
    return True
