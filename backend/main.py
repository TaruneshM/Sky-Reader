import logging
import os
import re
import time
from collections import Counter, deque
from threading import Lock
from typing import Annotated, Any, List, Optional
from fastapi import FastAPI, HTTPException, Header, Path, Request, Response
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, EmailStr, Field

try:
    from weather.service import (
        geocode_location,
        get_current_weather,
        format_current_weather,
        get_hourly_forecast,
        format_hourly_forecast,
    )
    from weather.models import WeatherResponse
    from weather.analysis import analyze_weather_data, get_weather_decision_support
    from agent.agent import run_agent
    from agent.failures import FailureCategory, RequestFailure
    from evidence.evidence_engine import EvidenceEngine
    from evidence.claim_extractor import ClaimExtractor
    from evidence.claim_validator import ClaimValidator
    from evidence.hallucination_controller import HallucinationController
    from evidence.explanation_engine import ExplanationEngine
    from database import (
        init_db,
        register_with_session,
        RegistrationRejected,
        authenticate_user,
        create_session,
        get_user_by_session_token,
        delete_session,
    )
except ImportError:
    from backend.weather.service import (
        geocode_location,
        get_current_weather,
        format_current_weather,
        get_hourly_forecast,
        format_hourly_forecast,
    )
    from backend.weather.models import WeatherResponse
    from backend.weather.analysis import analyze_weather_data, get_weather_decision_support
    from backend.agent.agent import run_agent
    from backend.agent.failures import FailureCategory, RequestFailure
    from backend.evidence.evidence_engine import EvidenceEngine
    from backend.evidence.claim_extractor import ClaimExtractor
    from backend.evidence.claim_validator import ClaimValidator
    from backend.evidence.hallucination_controller import HallucinationController
    from backend.evidence.explanation_engine import ExplanationEngine
    from backend.database import (
        init_db,
        register_with_session,
        RegistrationRejected,
        authenticate_user,
        create_session,
        get_user_by_session_token,
        delete_session,
    )


if __package__ == "backend":
    from . import conversation_store as thread_store
else:
    import conversation_store as thread_store


app = FastAPI(
    title="Sky Reader (WeatherGPT) API",
    description="Backend API for the Sky Reader agentic weather intelligence system.",
    version="0.2.0",
)


@app.on_event("startup")
def on_startup():
    init_db()


class UserRegisterRequest(BaseModel):
    email: EmailStr = Field(..., max_length=254, description="User's email address")
    password: str = Field(..., min_length=6, max_length=256, description="User's password (min 6 chars)")
    name: Optional[str] = Field(default="", max_length=120, description="User's full name")


class UserLoginRequest(BaseModel):
    email: str = Field(..., max_length=254, description="User's email address")
    password: str = Field(..., max_length=256, description="User's password")


class UserProfile(BaseModel):
    id: int
    email: str
    name: str
    created_at: str
    saved_cities: List[str] = []


class AuthResponse(BaseModel):
    user: UserProfile
    token: str
    message: str = "Success"


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://sky-reader-mauve.vercel.app",
    ],
    allow_origin_regex=r"(http://(localhost|127\.0\.0\.1):51\d\d|https://.*\.vercel\.app)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Thread-Revision"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    if request.url.path.startswith("/api/auth/"):
        return JSONResponse(status_code=422, content={"detail": "Check your information and try again."},
                            headers={"Cache-Control": "no-store"})
    return await request_validation_exception_handler(request, error)


THREAD_ID_PATTERN = r"^[A-Za-z0-9_-]{32}$"
ThreadId = Annotated[str, Path(pattern=THREAD_ID_PATTERN)]


class AgentChatRequest(BaseModel):
    thread_id: str | None = Field(default=None, pattern=THREAD_ID_PATTERN)
    thread_revision: int | None = Field(default=None, ge=0, le=2**53 - 1, strict=True)
    message: str = Field(..., max_length=4000, description="The user's weather question or general query.")
    conversation_history: Optional[List[dict]] = Field(
        default_factory=list,
        description="Optional list of prior conversation turns [{'role': 'user'|'assistant', 'content': str}]."
    )


class AgentChatResponse(BaseModel):
    response: str = Field(..., description="Natural language response generated by the agent.")
    tool_calls: List[dict] = Field(default_factory=list, description="List of tools invoked during reasoning.")
    iterations: int = Field(default=1, description="Number of tool-calling iterations performed.")
    claims: List[dict] = Field(default_factory=list, description="Extracted factual claims from the response.")
    validation_report: Optional[dict] = Field(None, description="Deterministic audit and hallucination report.")
    explanation: Optional[dict] = Field(None, description="Explanation proof and meteorological reasoning chain.")
    risk_assessment: Optional[dict] = Field(None, description="Deterministic weather safety and hazard assessment.")
    token_usage: Optional[dict] = Field(None, description="Deterministic token consumption and latency metrics.")


class ClaimValidationRequest(BaseModel):
    text: str = Field(..., description="Text containing weather statements or claims to validate.")
    location: str = Field(..., description="Location to fetch meteorological evidence for.")


evidence_engine_instance = EvidenceEngine()
claim_extractor_instance = ClaimExtractor()
claim_validator_instance = ClaimValidator()
hallucination_controller_instance = HallucinationController()
explanation_engine_instance = ExplanationEngine()


@app.get("/")
def root():
    return {
        "message": "Sky Reader backend is alive 🌦️"
    }


logger = logging.getLogger(__name__)


def bearer_token(authorization: Optional[str]) -> str:
    match = re.fullmatch(r"Bearer ([A-Za-z0-9_-]{43})", authorization or "", re.IGNORECASE)
    if not match:
        raise HTTPException(status_code=401, detail="Missing or invalid authentication token.")
    return match[1]


@app.post("/api/auth/register", response_model=AuthResponse)
def register_endpoint(request: UserRegisterRequest, response: Response):
    try:
        user_data, token = register_with_session(request.email, request.password, request.name or "")
    except RegistrationRejected:
        raise HTTPException(status_code=400, detail="Registration could not be completed.") from None
    except Exception:
        logger.error("Account registration failed category=internal_application_error")
        raise HTTPException(status_code=500, detail="Registration could not be completed.") from None
    response.headers["Cache-Control"] = "no-store"
    return AuthResponse(user=UserProfile(**user_data), token=token, message="User registration successful")


@app.post("/api/auth/login", response_model=AuthResponse)
def login_endpoint(request: UserLoginRequest, response: Response):
    user_data = authenticate_user(request.email, request.password)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = create_session(user_data["id"])
    response.headers["Cache-Control"] = "no-store"
    return AuthResponse(user=UserProfile(**user_data), token=token, message="Login successful")


@app.get("/api/auth/me", response_model=UserProfile)
def get_current_user_endpoint(response: Response, authorization: Optional[str] = Header(None)):
    user = get_user_by_session_token(bearer_token(authorization))
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid.")
    response.headers["Cache-Control"] = "no-store"
    return UserProfile(**user)


@app.post("/api/auth/logout")
def logout_endpoint(authorization: Optional[str] = Header(None)):
    delete_session(bearer_token(authorization))
    return {"message": "Logged out successfully"}


@app.get("/weather", response_model=WeatherResponse)
async def weather(location: str):

    place = await geocode_location(location)

    if place is None:
        raise HTTPException(
            status_code=404,
            detail=f"Could not find location: {location}"
        )

    current_data = await get_current_weather(
        place["latitude"],
        place["longitude"],
    )

    forecast_data = await get_hourly_forecast(
        place["latitude"],
        place["longitude"],
    )

    formatted_current = format_current_weather(
        place,
        current_data,
    )

    formatted_forecast = format_hourly_forecast(
        forecast_data,
        current_data["current"]["time"],
    )

    return {
        "location": formatted_current["location"],
        "current": formatted_current["current"],
        "forecast": formatted_forecast,
    }


@app.get("/api/weather/analysis")
@app.get("/weather/analysis", include_in_schema=False)
async def weather_analysis(location: str, focus: str = "all", day_offset: int = 1):
    place = await geocode_location(location)
    if place is None:
        raise HTTPException(
            status_code=404,
            detail=f"Could not find location: {location}"
        )
    forecast_data = await get_hourly_forecast(place["latitude"], place["longitude"])
    analysis_res = analyze_weather_data(forecast_data, focus=focus, day_offset=day_offset)
    return {
        "location": place,
        "analysis": analysis_res,
    }


@app.get("/api/weather/risks")
@app.get("/weather/risks", include_in_schema=False)
async def weather_risks(location: str, day_offset: int = 1):
    """
    Dedicated endpoint for Phase 6 deterministic weather safety, hazard detection,
    and risk assessment.
    """
    place = await geocode_location(location)
    if place is None:
        raise HTTPException(
            status_code=404,
            detail=f"Could not find location: {location}"
        )
    forecast_data = await get_hourly_forecast(place["latitude"], place["longitude"])
    try:
        from backend.weather.risk_engine import WeatherRiskEngine
    except ImportError:
        from weather.risk_engine import WeatherRiskEngine

    assessment = WeatherRiskEngine().assess_risks(
        forecast_data, day_offset=day_offset, location_name=place.get("name")
    )
    return {
        "location": place,
        "risk_assessment": assessment.dict(),
    }


class ChatRateLimit:
    """Bound the number of chat starts per minute in this process."""
    def __init__(self, per_client: int, total: int):
        if per_client < 1 or total < 1:
            raise ValueError("Chat rate limits must be positive.")
        self.per_client = per_client
        self.total = total
        self.requests = deque()
        self.counts = Counter()
        self.lock = Lock()

    def check(self, client: str):
        with self.lock:
            now = time.monotonic()
            while self.requests and self.requests[0][0] <= now - 60:
                _, expired_client = self.requests.popleft()
                self.counts[expired_client] -= 1
                if self.counts[expired_client] == 0:
                    del self.counts[expired_client]
            if len(self.requests) >= self.total or self.counts[client] >= self.per_client:
                raise HTTPException(status_code=429, detail="Chat request limit reached. Please try again shortly.",
                                    headers={"Retry-After": "60"})
            self.requests.append((now, client))
            self.counts[client] += 1


chat_rate_limit = ChatRateLimit(
    int(os.getenv("SKYREADER_CHAT_REQUESTS_PER_IP_PER_MINUTE", "12")),
    int(os.getenv("SKYREADER_CHAT_REQUESTS_PER_MINUTE", "60")),
)


lifecycle_rate_limit = ChatRateLimit(30, 180)


def thread_credentials(request: Request, *, guest_only: bool = False):
    authorization = request.headers.get("Authorization")
    guest = request.headers.get("X-Guest-Session")
    if authorization is not None:
        if guest is not None or guest_only:
            raise HTTPException(status_code=401, detail="Provide one valid conversation credential.")
        return thread_store.Credentials(bearer=bearer_token(authorization))
    if not guest or not re.fullmatch(r"[A-Za-z0-9_-]{43}", guest):
        raise HTTPException(status_code=401, detail="A valid conversation credential is required.")
    return thread_store.Credentials(guest=guest)


def thread_operation(operation, *args):
    try:
        return operation(*args)
    except thread_store.InvalidOwner:
        raise HTTPException(status_code=401, detail="The conversation session has ended.") from None
    except thread_store.ThreadNotFound:
        raise HTTPException(status_code=404, detail="Conversation thread not found.") from None
    except thread_store.ThreadConflict as error:
        raise HTTPException(
            status_code=409, detail="The conversation changed. Send your next message again.",
            headers={"X-Thread-Revision": str(error.revision), "Cache-Control": "no-store"},
        ) from None
    except thread_store.IncompatibleState:
        raise HTTPException(status_code=409, detail="This conversation state is unavailable. Start a new chat.") from None


def check_lifecycle_limit(request: Request):
    lifecycle_rate_limit.check(request.client.host if request.client else "unknown")


@app.post("/api/guest/session", status_code=201)
def create_guest_session(request: Request, response: Response):
    check_lifecycle_limit(request)
    response.headers["Cache-Control"] = "no-store"
    return {"credential": thread_store.create_guest()}


@app.delete("/api/guest/session", status_code=204)
def revoke_guest_session(request: Request):
    check_lifecycle_limit(request)
    thread_store.revoke_guest(thread_credentials(request, guest_only=True))


@app.post("/api/chat/threads", status_code=201)
def create_chat_thread(request: Request, response: Response):
    check_lifecycle_limit(request)
    thread_id = thread_operation(thread_store.create_thread, thread_credentials(request))
    response.headers["Cache-Control"] = "no-store"
    return {"thread_id": thread_id, "thread_revision": 0}


@app.delete("/api/chat/threads", status_code=204)
def clear_chat_threads(request: Request):
    check_lifecycle_limit(request)
    thread_operation(thread_store.clear_threads, thread_credentials(request))


@app.delete("/api/chat/threads/{thread_id}", status_code=204)
def delete_chat_thread(thread_id: ThreadId, request: Request):
    check_lifecycle_limit(request)
    thread_operation(thread_store.clear_threads, thread_credentials(request), thread_id)


def log_chat_metrics(usage: dict, started: float, *, failure: FailureCategory | None = None):
    usage["request_total_latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    if failure:
        usage["failure_category"] = failure.value
    logging.getLogger("skyreader.token_metrics").info(
        "Chat metrics prompt=%s completion=%s attempted=%s completed=%s tools=%s planner_ms=%s "
        "llm_ms=%s weather_ms=%s weather_attempts=%s total_ms=%s failure=%s deterministic_fallback=%s "
        "deterministic_selected=%s answer_complete=%s estimated_llm_calls_avoided=%s",
        usage.get("prompt_tokens"), usage.get("completion_tokens"), usage.get("llm_calls_attempted"),
        usage.get("llm_calls_completed"), usage.get("tool_calls_count"), usage.get("planner_latency_ms"),
        usage.get("llm_latency_ms"), usage.get("weather_provider_latency_ms"), usage.get("weather_http_attempts"),
        usage["request_total_latency_ms"], usage.get("failure_category"), usage.get("deterministic_fallback"),
        usage.get("deterministic_selected"), usage.get("answer_complete"), usage.get("estimated_llm_calls_avoided"),
    )


@app.post("/api/agent/chat", response_model=AgentChatResponse)
@app.post("/agent/chat", response_model=AgentChatResponse, include_in_schema=False)
async def agent_chat(request: AgentChatRequest, http_request: Request, response: Response):
    started = time.perf_counter()
    message = request.message.strip()
    if not message:
        raise HTTPException(
            status_code=400,
            detail="The 'message' field cannot be empty."
        )

    chat_rate_limit.check(http_request.client.host if http_request.client else "unknown")

    credentials = state = None
    if request.thread_id is not None:
        if request.thread_revision is None:
            raise HTTPException(status_code=422, detail="A thread revision is required.")
        credentials = thread_credentials(http_request)
        state = await run_in_threadpool(
            thread_operation, thread_store.load_thread, credentials, request.thread_id, request.thread_revision,
        )
    elif request.thread_revision is not None:
        raise HTTPException(status_code=422, detail="A thread ID is required with a thread revision.")

    try:
        # Sanitize and cap conversation history (last 6 turns max = 3 exchanges to avoid prompt bloat)
        history = request.conversation_history or []
        trimmed_history = []
        for msg in history[-6:]:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                role = str(msg["role"]).lower()
                if role in ("user", "assistant"):
                    trimmed_history.append({"role": role, "content": str(msg["content"])[:4000]})

        planner_options = {"trusted_state": state, "request_scope": state.scope} if state is not None else {}
        result = await run_agent(message, conversation_history=trimmed_history, **planner_options)
        token_usage = result.get("token_usage")
        answer = AgentChatResponse(
            response=result["response"],
            tool_calls=result.get("tool_calls", []),
            iterations=result.get("iterations", 1),
            claims=result.get("claims", []),
            validation_report=result.get("validation_report"),
            explanation=result.get("explanation"),
            risk_assessment=result.get("risk_assessment"),
            token_usage=token_usage,
        )
        if state is not None:
            if await http_request.is_disconnected():
                raise HTTPException(status_code=409, detail="The conversation request was cancelled.")
            revision = await run_in_threadpool(
                thread_operation, thread_store.save_thread, credentials, request.thread_id, request.thread_revision,
                result.get("conversation_state") or state,
            )
            response.headers["X-Thread-Revision"] = str(revision)
            response.headers["Cache-Control"] = "no-store"
        if token_usage is not None:
            log_chat_metrics(token_usage, started)
            answer.token_usage = token_usage
        return answer
    except HTTPException:
        raise
    except RequestFailure as error:
        metrics = error.metrics or {}
        log_chat_metrics(metrics, started, failure=error.category)
        headers = {"Cache-Control": "no-store"}
        if error.retry_after is not None:
            headers["Retry-After"] = str(error.retry_after)
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.detail, "error": {"category": error.category.value}, "token_usage": metrics},
            headers=headers,
        )
    except Exception:
        error = RequestFailure(FailureCategory.INTERNAL)
        metrics = {}
        log_chat_metrics(metrics, started, failure=error.category)
        return JSONResponse(status_code=error.status_code, content={
            "detail": error.detail, "error": {"category": error.category.value}, "token_usage": metrics,
        }, headers={"Cache-Control": "no-store"})


@app.post("/api/evidence/validate")
@app.post("/evidence/validate", include_in_schema=False)
async def validate_claims_endpoint(request: ClaimValidationRequest):
    """
    Validates factual weather statements deterministically against live Open-Meteo observations
    and Phase 3 analytical outputs.
    """
    place = await geocode_location(request.location)
    if place is None:
        raise HTTPException(status_code=404, detail=f"Location not found: {request.location}")

    current_data = await get_current_weather(place["latitude"], place["longitude"])
    hourly_data = await get_hourly_forecast(place["latitude"], place["longitude"])
    analysis_res = analyze_weather_data(hourly_data, focus="all", day_offset=1)
    rec_res = get_weather_decision_support(hourly_data, day_offset=1)
    combined_analysis = {**analysis_res, **rec_res}

    evidence = evidence_engine_instance.generate_evidence(
        current_data=current_data,
        hourly_data=hourly_data,
        location_meta=place,
        analysis_results=combined_analysis,
    )

    claims = claim_extractor_instance.extract_claims(request.text, default_location=place.get("name"))
    val_results = claim_validator_instance.validate_all(claims, evidence)
    report = hallucination_controller_instance.evaluate_claims(val_results)
    proof = explanation_engine_instance.generate_proof(
        query=f"Validate claims for {request.location}",
        response_text=request.text,
        evidence=evidence,
        report=report,
        validation_results=val_results,
    )

    return {
        "location": place,
        "claims": [c.dict() for c in claims],
        "validation_results": [r.dict() for r in val_results],
        "hallucination_report": report.dict(),
        "explanation_proof": proof.dict(),
    }


@app.get("/api/evidence/summary")
@app.get("/evidence/summary", include_in_schema=False)
async def evidence_summary_endpoint(location: str):
    """
    Retrieves the complete structured meteorological evidence collection and provenance records
    for a location.
    """
    place = await geocode_location(location)
    if place is None:
        raise HTTPException(status_code=404, detail=f"Location not found: {location}")

    current_data = await get_current_weather(place["latitude"], place["longitude"])
    hourly_data = await get_hourly_forecast(place["latitude"], place["longitude"])
    analysis_res = analyze_weather_data(hourly_data, focus="all", day_offset=1)
    rec_res = get_weather_decision_support(hourly_data, day_offset=1)
    combined_analysis = {**analysis_res, **rec_res}

    evidence = evidence_engine_instance.generate_evidence(
        current_data=current_data,
        hourly_data=hourly_data,
        location_meta=place,
        analysis_results=combined_analysis,
    )

    return {
        "location": place,
        "evidence_count": len(evidence.items),
        "evidence_summary": evidence.to_summary_dict(),
        "items": [it.dict() for it in evidence.items],
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Sky Reader backend"
    }


@app.get("/api/diag")
async def diag(location: str = "Dehradun"):
    import traceback
    out = {}
    try:
        place = await geocode_location(location)
        out["geocode"] = place
        if not place:
            return out
    except Exception as e:
        out["geocode_error"] = str(e)
        out["geocode_tb"] = traceback.format_exc()
        return out

    try:
        current = await get_current_weather(place["latitude"], place["longitude"])
        out["current_sample"] = {k: v for k, v in current.items() if k != "hourly"}
    except Exception as e:
        out["current_error"] = str(e)
        out["current_tb"] = traceback.format_exc()
        return out

    try:
        hourly = await get_hourly_forecast(place["latitude"], place["longitude"])
        out["hourly_keys"] = list(hourly.keys())
    except Exception as e:
        out["hourly_error"] = str(e)
        out["hourly_tb"] = traceback.format_exc()

    return out
