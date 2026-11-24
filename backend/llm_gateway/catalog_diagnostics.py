"""Approval-gated metadata probe. Importing this module performs no I/O."""

import argparse
import asyncio
from decimal import Decimal, InvalidOperation
import json
import os
import re

import httpx

from .config import FREE_MODELS, KEYS, model_for


GEMINI_CATALOG = "https://generativelanguage.googleapis.com/v1beta/models"
OPENROUTER_CATALOG = "https://openrouter.ai/api/v1/models"
TIMEOUT = 15
BODY_LIMIT = 8 * 1024 * 1024
# Emit only recognized method names, never arbitrary provider-controlled strings.
GEMINI_METHODS = frozenset({
    "generateContent", "streamGenerateContent", "batchGenerateContent", "bidiGenerateContent",
    "countTokens", "embedContent", "batchEmbedContents", "asyncBatchEmbedContent",
    "asyncBatchGenerateContent", "createCachedContent", "createTunedModel", "generateAnswer",
    "generateText", "generateMessage", "countTextTokens", "countMessageTokens",
    "predict", "predictLongRunning",
})


async def _catalog(client, url, headers, params=None):
    try:
        async with asyncio.timeout(TIMEOUT), client.stream("GET", url, headers=headers, params=params) as response:
            if not response.is_success or response.headers.get("content-encoding", "identity").lower() != "identity":
                return None
            body = bytearray()
            async for chunk in response.aiter_bytes(32 * 1024):
                if len(body) + len(chunk) > BODY_LIMIT:
                    return None
                body.extend(chunk)
            data = json.loads(body, parse_float=Decimal)
            return data if isinstance(data, dict) else None
    except (httpx.HTTPError, TimeoutError, ValueError, RecursionError, InvalidOperation):
        return None


def _match(catalog, field, id_field, target, *, incomplete):
    rows = catalog.get(field) if catalog is not None else None
    if not isinstance(rows, list):
        return None, None
    for row in rows:
        if isinstance(row, dict) and row.get(id_field) == target:
            return True, row
    if incomplete or any(not isinstance(row, dict) or not isinstance(row.get(id_field), str) for row in rows):
        return None, None
    return False, None


def _gemini_summary(catalog, model):
    found, row = _match(
        catalog, "models", "name", f"models/{model.removeprefix('models/')}",
        incomplete=bool(catalog and catalog.get("nextPageToken")),
    )
    methods = row.get("supportedGenerationMethods") if row is not None else None
    return {
        "model_listed": found,
        "supported_generation_methods": sorted({
            item for item in methods if isinstance(item, str) and item in GEMINI_METHODS
        }) if isinstance(methods, list) else None,
    }


def _zero_price(value):
    if type(value) not in (str, int, Decimal) or (isinstance(value, str) and len(value) > 64):
        return None
    try:
        price = Decimal(value)
        return price.is_zero() if price.is_finite() and price >= 0 else None
    except (InvalidOperation, ValueError):
        return None


def _openrouter_summary(catalog, model):
    rows = catalog.get("data") if catalog is not None else None
    total = catalog.get("total_count") if catalog is not None else None
    found, row = _match(
        catalog, "data", "id", model,
        incomplete=type(total) is int and isinstance(rows, list) and total > len(rows),
    )
    pricing = row.get("pricing") if row is not None else None
    prompt, completion = (
        (_zero_price(pricing.get("prompt")), _zero_price(pricing.get("completion")))
        if isinstance(pricing, dict) else (None, None)
    )
    zero_price = False if False in (prompt, completion) else None if None in (prompt, completion) else True
    endpoints = row.get("endpoints") if row is not None else None
    return {
        "model_listed": found,
        "zero_prompt_and_completion_price": zero_price,
        "serving_endpoints_listed": bool(endpoints) if isinstance(endpoints, list) else None,
    }


async def inspect_catalogs(gemini_model, gemini_key, openrouter_model, openrouter_key, *, transport=None):
    """Fetch only the two fixed catalog URLs, sequentially and once each."""
    async with httpx.AsyncClient(
        timeout=TIMEOUT, follow_redirects=False, trust_env=False,
        transport=transport if transport is not None else httpx.AsyncHTTPTransport(retries=0, trust_env=False),
        headers={"Accept": "application/json", "Accept-Encoding": "identity"},
    ) as client:
        gemini = await _catalog(client, GEMINI_CATALOG, {"x-goog-api-key": gemini_key}, {"pageSize": 1000})
        openrouter = await _catalog(client, OPENROUTER_CATALOG, {"Authorization": f"Bearer {openrouter_key}"})
    return {
        "gemini": _gemini_summary(gemini, gemini_model),
        "openrouter": _openrouter_summary(openrouter, openrouter_model),
    }


def main():
    parser = argparse.ArgumentParser(description="Check the configured Gemini and OpenRouter model catalogs.")
    parser.add_argument("--live", action="store_true", required=True, help="Opt in to two authenticated catalog GETs.")
    parser.parse_args()
    gemini_model, openrouter_model = model_for("gemini"), model_for("openrouter")
    gemini_key = os.getenv(KEYS["gemini"], "").strip()
    openrouter_key = os.getenv(KEYS["openrouter"], "").strip()
    if not (gemini_key and openrouter_key):
        parser.error("Set both provider credentials in the process environment.")
    if not re.fullmatch(r"(?:models/)?[A-Za-z0-9][A-Za-z0-9._-]{0,127}", gemini_model):
        parser.error("Set a valid GEMINI_MODEL in the process environment.")
    if openrouter_model not in FREE_MODELS:
        parser.error("Set OPENROUTER_MODEL to a model on the existing free-model allowlist.")
    results = asyncio.run(inspect_catalogs(gemini_model, gemini_key, openrouter_model, openrouter_key))
    print(json.dumps(results, indent=2))
    return int(any(result["model_listed"] is None for result in results.values()))


if __name__ == "__main__":
    raise SystemExit(main())
