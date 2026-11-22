"""Safe failure categories shared by the agent and the chat API."""

from enum import Enum

import httpx
import re

from groq import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, RateLimitError


class FailureCategory(str, Enum):
    AMBIGUOUS = "geocoding_ambiguity"
    LOCATION_NOT_FOUND = "location_not_found"
    WEATHER_PROVIDER_UNAVAILABLE = "weather_provider_unavailable"
    FORECAST_WINDOW_UNAVAILABLE = "forecast_window_unavailable"
    GROQ_QUOTA_EXHAUSTED = "groq_quota_exhausted"
    GROQ_THROTTLED = "groq_temporary_throttling"
    GROQ_AUTHENTICATION = "groq_authentication_failure"
    GROQ_TIMEOUT = "groq_timeout"
    LLM_BUDGET_EXHAUSTED = "llm_budget_exhausted"
    GROQ_SERVICE = "groq_service_failure"
    LLM_UNAVAILABLE = "llm_provider_unavailable"
    LLM_THROTTLED = "llm_provider_throttled"
    LLM_AUTHENTICATION = "llm_provider_authentication_failure"
    LLM_TIMEOUT = "llm_provider_timeout"
    LLM_SERVICE = "llm_provider_service_failure"
    INTERNAL = "internal_application_error"


_FAILURE_RESPONSES = {
    FailureCategory.WEATHER_PROVIDER_UNAVAILABLE: (503, "The weather provider is unavailable right now."),
    FailureCategory.GROQ_QUOTA_EXHAUSTED: (429, "Sky Reader has reached its AI usage limit for now."),
    FailureCategory.GROQ_THROTTLED: (429, "Sky Reader is temporarily rate limited. Please try again shortly."),
    FailureCategory.GROQ_AUTHENTICATION: (503, "Sky Reader’s AI service is unavailable."),
    FailureCategory.GROQ_TIMEOUT: (504, "Sky Reader’s AI service timed out."),
    FailureCategory.LLM_BUDGET_EXHAUSTED: (503, "Sky Reader could not complete the answer within its reasoning limits."),
    FailureCategory.GROQ_SERVICE: (502, "Sky Reader’s AI service could not complete the request."),
    FailureCategory.LLM_UNAVAILABLE: (503, "The selected AI provider is unavailable."),
    FailureCategory.LLM_THROTTLED: (429, "The selected AI provider is rate limited."),
    FailureCategory.LLM_AUTHENTICATION: (503, "The selected AI provider could not authenticate."),
    FailureCategory.LLM_TIMEOUT: (504, "The selected AI provider timed out."),
    FailureCategory.LLM_SERVICE: (502, "The selected AI provider returned an invalid or unsuccessful response."),
    FailureCategory.INTERNAL: (500, "Sky Reader encountered an unexpected issue while processing your request."),
}


class RequestFailure(Exception):
    def __init__(self, category: FailureCategory, *, retry_after: int | None = None, metrics: dict | None = None,
                 provider_status: int | None = None, transient: bool = False,
                 dispatched: bool | None = None):
        self.category = category
        self.status_code, self.detail = _FAILURE_RESPONSES[category]
        self.retry_after = retry_after
        self.metrics = metrics
        self.provider_status = provider_status
        self.transient = transient
        self.dispatched = dispatched
        self.provider = None
        self.replay_safe = False
        super().__init__(self.detail)


def classify_groq_failure(error: Exception) -> RequestFailure:
    if isinstance(error, RateLimitError):
        headers = error.response.headers
        # Use provider metadata when available, then inspect a bounded error message.
        message = str(error.message)[:1000]
        daily = headers.get("x-ratelimit-remaining-requests") == "0" or re.search(
            r"\b(?:daily|(?:requests|tokens) per day|rpd|tpd)\b", message, re.I
        )
        raw_retry = headers.get("retry-after", "")
        retry_after = int(raw_retry) if re.fullmatch(r"\d{1,8}", raw_retry) else None
        return RequestFailure(FailureCategory.GROQ_QUOTA_EXHAUSTED if daily else FailureCategory.GROQ_THROTTLED,
                              retry_after=retry_after, provider_status=429, transient=True, dispatched=True)
    if isinstance(error, AuthenticationError) or (isinstance(error, APIStatusError) and error.status_code in {401, 403}):
        return RequestFailure(FailureCategory.GROQ_AUTHENTICATION, provider_status=error.status_code, dispatched=True)
    if isinstance(error, APITimeoutError):
        return RequestFailure(FailureCategory.GROQ_TIMEOUT, transient=True)
    if isinstance(error, APIStatusError):
        return RequestFailure(FailureCategory.GROQ_SERVICE, provider_status=error.status_code,
                              transient=error.status_code in {502, 503, 504}, dispatched=True)
    if isinstance(error, APIConnectionError):
        return RequestFailure(FailureCategory.GROQ_SERVICE,
                              transient=isinstance(error.__cause__, httpx.ConnectError))
    return RequestFailure(FailureCategory.INTERNAL)
