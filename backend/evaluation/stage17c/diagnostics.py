"""Bounded diagnostics for synthetic validation. Never persist provider prose."""
import json
import re

from backend.agent.answer_completeness import requirements
from backend.agent.weather_evidence_gate import first_weather_gate_rejection
from backend.evidence.evidence_engine import EvidenceEngine
from backend.evidence.hallucination_controller import HallucinationController

ERROR_BYTES = 2048
KNOWN_CODES = frozenset({
    "NOT_FOUND", "INVALID_ARGUMENT", "PERMISSION_DENIED", "UNAUTHENTICATED",
    "RESOURCE_EXHAUSTED", "UNAVAILABLE", "DEADLINE_EXCEEDED", "INTERNAL",
    "model_not_found", "invalid_request_error", "rate_limit_exceeded", "authentication_error",
})
KNOWN_STATUSES = frozenset({400, 401, 403, 404, 408, 409, 413, 422, 429, 500, 502, 503, 504})
ENDPOINT_IDS = {"groq": "groq_chat_completions", "gemini": "gemini_generate_content",
                "openrouter": "openrouter_chat_completions"}


def error_diagnostic(provider, model, status, body):
    # Provider text is used only to select a fixed paraphrase. Even unknown secret formats
    # cannot leak through copied substrings, nested metadata, endpoint URLs or request fields.
    try:
        envelope = json.loads(body) if len(body) <= ERROR_BYTES else {}
        error = envelope.get("error", {}) if type(envelope) is dict else {}
    except (ValueError, UnicodeError, RecursionError):
        error = {}
    if type(error) is not dict:
        error = {}
    markers = [error.get(key) for key in ("status", "type", "code")]
    code = next((value for value in markers if
                 (type(value) is str and value in KNOWN_CODES) or
                 (type(value) is int and value in KNOWN_STATUSES)), None)
    message = error.get("message")
    message = message[:512].casefold() if type(message) is str else ""
    if re.search(r"no endpoints found|no (?:eligible )?provider", message):
        summary = "No matching provider endpoint was reported."
    elif re.search(r"(?:model\b.*(?:not found|not supported|does not exist)|unknown model)", message):
        summary = "The provider reported that the requested model was unavailable or unsupported."
    elif status in {401, 403}:
        summary = "The provider rejected authentication or authorization."
    elif status == 429:
        summary = "The provider rejected the request because of a usage limit."
    elif status == 404:
        summary = "The provider reported a missing resource or endpoint."
    else:
        summary = "The provider rejected the request."
    return {
        "provider": provider, "model": model, "endpoint_id": ENDPOINT_IDS[provider],
        "http_status": status, "provider_code": code, "sanitized_message": summary,
        "retryable": status in {429, 502, 503, 504},
        "fallback_allowed": False,  # This diagnostic applies to the final live target only.
    }


def draft_diagnostic(response, prompt, observation, place, output_cap):
    draft = response.message.get("content") or ""
    evidence = EvidenceEngine().generate_evidence(current_data=observation, location_meta=place)
    auditor = HallucinationController()
    _, report = auditor.audit(draft, evidence)
    criteria = requirements("temperature", prompt, forecast=False, components=("temperature",))
    usage = response.usage.completion_tokens
    finish = response.finish_reason
    valid_finish = {"stop", "length", "tool_calls", "content_filter", "STOP", "MAX_TOKENS", "SAFETY"}
    rejection = first_weather_gate_rejection(draft, evidence, auditor, weather_request=True)
    matched = sorted({item_id for row in report.validation_results if row.status.value == "SUPPORTED"
                      for item_id in row.supporting_evidence_ids})[:8]
    return {
        "supporting_fixture_evidence_ids": matched,
        "claim_validation": [
            {"variable": row.claim.variable.value, "status": row.status.value,
             "supporting_evidence_ids": row.supporting_evidence_ids[:8]}
            for row in report.validation_results[:16]
        ],
        "final_gate_rejection": rejection,
        "draft_audited": report.is_trustworthy,
        "draft_passed_model_evidence_gate": rejection is None,
        "missing_requirements": criteria.omissions(draft, report, evidence, location=place["name"]),
        "unsupported_claims": [
            {"variable": row.claim.variable.value, "status": row.status.value}
            for row in report.validation_results if row.status.value != "SUPPORTED"
        ],
        "named_location_present": bool(re.search(r"(?<!\w)" + re.escape(place["name"]) + r"(?!\w)", draft, re.I)),
        "temperature_units_present": bool(re.search(r"°\s*[CF]|\bdegrees?\b|\b(?:celsius|fahrenheit)\b", draft, re.I)),
        "finish_reason": finish if finish in valid_finish else None,
        "truncated": None if finish not in valid_finish else finish in {"length", "MAX_TOKENS"},
        "output_cap": output_cap,
        "reported_usage_reached_cap": None if usage is None else usage >= output_cap,
    }
