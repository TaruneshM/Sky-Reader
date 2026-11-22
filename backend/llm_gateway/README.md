# Sky Reader LLM gateway

The existing Sky Reader agent owns weather preparation, tool execution, evidence validation and request budgets. It creates a gateway only when it needs model output. The gateway dispatches one bounded request to the selected adapter and returns a normalized assistant message and usage. The same adapter handles any later tool turns or corrections within the original request budget.

## Configuration

| Setting | Behavior |
|---|---|
| `LLM_PROVIDER` | Default selection is `groq`. Deployments may explicitly choose `gemini` or `openrouter`. Backend code may pass `provider=` to `run_agent`. |
| `LLM_ENABLED_PROVIDERS` | Comma-separated enabled providers. Defaults to `groq`. Existing injected Groq clients remain available for test and evaluation callers. |
| `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY` | Server-side credentials. Keep them in the deployment environment or ignored dotenv file. |
| `GROQ_MODEL`, `GEMINI_MODEL`, `OPENROUTER_MODEL` | Gemini and OpenRouter require an explicit model. Groq defaults to `openai/gpt-oss-120b`. |
| `GROQ_TIMEOUT_SECONDS`, `GEMINI_TIMEOUT_SECONDS`, `OPENROUTER_TIMEOUT_SECONDS` | Optional, positive and at most 120 seconds. Groq retains the SDK default when unset. Gemini and OpenRouter default to 30 seconds. |

The client cannot choose a provider via the chat payload. An unavailable configuration returns a safe typed error when model execution is needed. Groq retains its existing error categories and zero SDK retries.

## Protocol and adapter limits

- The normalized protocol supports textual system, user, assistant and tool messages, function definitions, named JSON arguments, matching tool-call IDs, finish reasons and usage. Multimedia, streaming and arbitrary extensions are outside this stage.
- Groq reuses the existing SDK and the explicitly selected SDK fields accepted by the bounded serializer. Stage 1.6.5's injected client remains the dispatch target when supplied.
- Gemini uses the Google `generateContent` REST endpoint. System messages become ordered system instructions and conversation turns retain their relative order. Parallel function responses go in a single user turn. The adapter keeps bounded, request-local function-call parts so provider IDs and opaque signatures can be replayed. It supplies local correlation IDs for calls without provider IDs. Signed text parts and mixed text/function turns are rejected. [Google thought signatures](https://ai.google.dev/gemini-api/docs/thought-signatures)
- OpenRouter uses Chat Completions with a checked-in exact free-model allowlist, zero maximum prompt/completion price, required parameter support, and provider fallback disabled. A listed model still might be unavailable. Reasoning metadata on tool turns is rejected because faithful replay is outside this stage. [OpenRouter provider configuration](https://openrouter.ai/docs/guides/routing/provider-selection)
- Usage remains unknown when a provider omits it. Gemini's separately reported thought tokens are counted in output usage when output usage is available. Telemetry records the selected provider without storing prompts or secrets.
- REST adapters use fixed HTTPS origins, disable redirects and environment proxies, and cap response reads. The bounded serializer rejects arbitrary object graphs and oversized fields. Provider error bodies are not included in user-facing errors. Cancellation propagates and does not dispatch another request.

## Stage 1.7B fallback

The default remains single-provider Groq. To opt into fallback, set
`LLM_FALLBACK_ENABLED=true` and include each available provider in
`LLM_ENABLED_PROVIDERS`. Credentials stay in their existing environment variables.
`LLM_PROVIDER_ORDER` is an optional comma-separated priority list, defaulting to
`groq,gemini,openrouter`. Disabled providers, missing credentials or models, and
OpenRouter models outside the free allowlist are skipped. The validated priority has
no duplicates. Set `LLM_PROVIDER` for single-provider deployments. An explicit
`run_agent(provider=...)` selection or an injected client always pins the request.

Only the first, replay-safe model turn may change providers. The agent rebuilds
the normalized request with the next provider's configured model, the original
user/context text, and any prepared weather evidence. Weather fetching and tool
execution remain in the original request. After any provider has returned a model
turn, later tool rounds and evidence corrections stay on that provider. This
conservative policy declines cross-provider replay even when the prior tool results
might be portable. It never transfers SDK objects or reasoning metadata.

HTTP 429, 502, 503, and 504, clear connect failures and provider timeouts can
permit fallback on that first turn. Ambiguous transport failures, invalid requests,
authentication failures, malformed output, unsafe serialization, evidence failures,
cancellation and budget exhaustion stop migration. Numeric Retry-After is retained
in telemetry and in terminal 429 API responses where supported. A failed provider is
never revisited within the request, so switching to a different provider requires no
wait for the prior provider to recover.

Each attempt reserves from the same attempt, estimated input and output budgets.
Known provider usage reconciles its reservation. Unknown usage remains unknown and
keeps the conservative reservation. Tool rounds and corrections keep their
existing caps. The monotonic model deadline starts at agent entry and is checked
before dispatch. A running model call is cancelled when that deadline expires.
Weather preparation retains its own transport timeout and retry policy.

Telemetry records the configured first provider, actual attempt sequence, most
recent successful provider response, fallback transitions, HTTP status when
known, dispatch certainty, replay eligibility, latency, and provider-specific known
token totals with unknown counts. A successful provider response can still fail the
evidence audit. No prompts, headers or provider error bodies are included.
