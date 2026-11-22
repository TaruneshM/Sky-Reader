# Stage 1.7C preflight

**Awaiting approval. No live API calls were made.**

The production agent and its gateway ran with fake HTTP transports. The planner received a synthetic Lisbon observation of 21 °C and correct location identity. No weather-provider calls are needed. The production evidence gate and completeness check must both pass, and the harness independently checks that the supported temperature matches the fixture.

## Proposed live matrix

All cases ask **“Explain the current temperature in Lisbon, Portugal.”** The first case selects Groq explicitly. The second and third use the production fallback mode. Their earlier provider failures are injected into the HTTP transport before network dispatch. This design validates each real endpoint independently while exercising both fallback routes within the one-request-per-provider ceiling. Explicit selection for all three providers was also verified offline.

| Case | Simulated attempts | Only live attempt | Proposed model |
|---|---|---|---|
| Groq | None | Groq | `openai/gpt-oss-120b` |
| Gemini | Groq HTTP 429 | Gemini | `gemini-2.5-flash` |
| OpenRouter | Groq HTTP 429, Gemini HTTP 503 | OpenRouter | `qwen/qwen3-coder:free` |

Credential assignments were detected for all three providers without displaying their values. No explicit Gemini or OpenRouter model ID or provider enablement setting was detected. The command below proposes explicit, run-local selections. The Gemini and OpenRouter IDs are candidates whose live availability is unverified. The OpenRouter ID is on the repository's exact free allowlist. The harness requires a matching model and zero maximum prompt and completion prices, rejects model lists, and enforces provider-side fallback off. An unavailable model can fail the case. There is no paid fallback.

Maximum live dispatches are **three total, one per provider**, with no weather HTTP and no tool calls. Each HTTP request has a **350-token output cap**. Each case shares at most three model attempts including injected failures, 6,000 estimated input tokens, and 1,050 reserved output tokens. No corrections, retries, or redirects are enabled. The endpoint guard requires exact HTTPS POST URLs, limits response bodies to 192 KiB, and records only safe counts, status, timing, and usage. Transport deadlines are eight seconds, with a 20-second model deadline per case and a 65-second suite ceiling. The receipt stays consumed on failure or cancellation.

| Provider | Exact endpoint pattern |
|---|---|
| Groq | `https://api.groq.com/openai/v1/chat/completions` |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent` |
| OpenRouter | `https://openrouter.ai/api/v1/chat/completions` |

## Mocked verification

| Check | Result | Peak cgroup memory |
|---|---|---:|
| Harness | 4 passed | 75.7 MiB |
| Gateway and fallback, including tool turns and timeout handling | 33 passed | 76.5 MiB |
| Backend | 337 passed | 88.2 MiB |
| Frozen 120-case evaluation | Passed all gates | 40.8 MiB |

The frozen evaluation retained 101/120 completeness, 12/12 hazard coverage, 7/8 both-city coverage, 88/88 audited outputs grounded, and zero unaudited numerical answers. All runs used verified 512 MiB soft, 768 MiB hard, and zero-swap limits. There were no OOM events. The first harness run exposed cold-start budget exhaustion because failed attempts keep their output reservations. The shorter prompt uses the production 350-token tier and leaves room for all three reservations. The final harness tests passed independently and in the full suite.

The live results file will identify provider responses, network failures and injected outcomes separately, with per-attempt latency, observed response bytes, actual usage or unknown usage, evidence and completeness, and cgroup peak. Authentication, model availability, live text generation and live latency remain unverified. Timeout behavior and tool calls were exercised offline. No live tool-call test is proposed.

## Command proposed for fresh approval

Run from the repository root, once. The command checks memory protection before invoking Python, and the runner checks it again.

```bash
systemd-run --user --scope --quiet \
  -p MemoryHigh=512M -p MemoryMax=768M -p MemorySwapMax=0 \
  /bin/bash -c '
    base="/sys/fs/cgroup$(cut -d: -f3 /proc/self/cgroup)"
    [[ $(cat "$base/memory.high") == 536870912 &&
       $(cat "$base/memory.max") == 805306368 &&
       $(cat "$base/memory.swap.max") == 0 ]] || exit 99
    PYTHONDONTWRITEBYTECODE=1 LLM_ENABLED_PROVIDERS=groq,gemini,openrouter \
      GROQ_MODEL=openai/gpt-oss-120b GEMINI_MODEL=gemini-2.5-flash \
      OPENROUTER_MODEL=qwen/qwen3-coder:free \
      timeout -k 2s 70s /home/victus/ml_env/bin/python \
      -m backend.evaluation.stage17c.runner --live \
      --approval-receipt backend/evaluation/stage17c/live.used \
      --output backend/evaluation/stage17c/live-results.json
    status=$?
    printf "exit=%s peak_bytes=%s\n" "$status" "$(cat "$base/memory.peak")"
    cat "$base/memory.events"
    exit "$status"
  '
```

## Approved live run

**NOT READY — FIX REQUIRED.** The approved matrix ran once. It made three outbound requests, one per approved provider, and zero weather API calls. The receipt was consumed. There were no retries, redirects, or model substitutions. Exit status was **1**.

| Live provider and model | HTTP result | Case latency | Live model attempt latency | Response bytes read | Actual input / output tokens | Grounding and completeness |
|---|---|---:|---:|---:|---:|---|
| Groq `openai/gpt-oss-120b` | 200, normalized response | 1,074.32 ms | 1,063.03 ms | 1,521 | 224 / 191 | Audit and completeness failed |
| Gemini `gemini-2.5-flash` | 404, typed provider service failure | 459.37 ms | 454.86 ms | 0 | Unknown / unknown | No answer to audit |
| OpenRouter `qwen/qwen3-coder:free` | 404, typed provider service failure | 590.84 ms | 583.82 ms | 0 | Unknown / unknown | No answer to audit |

The runner read no error bodies for the two 404 responses. The status confirms each approved request was rejected, while the specific reason is unverified. The Groq response reached the production checks, but the recorded audit and completeness flags were false. The runner does not retain draft prose or claim-level audit details, so this run cannot identify the missing or unsupported clause. No case passed the live grounding-and-completeness criterion.

The Gemini case injected a local Groq 429, then dispatched only Gemini. The OpenRouter case injected a local Groq 429 and Gemini 503, then dispatched only OpenRouter. Telemetry recorded both expected transitions. This verifies that simulated upstream failures route to the intended live endpoint. It does not establish successful live recovery, since both final providers returned 404. The OpenRouter request used the approved free model with both price ceilings set to zero and provider fallback disabled.

Peak cgroup memory was **44,187,648 bytes (42.1 MiB)** under verified 512 MiB soft, 768 MiB hard, and zero-swap limits. There were zero OOM events. The [machine-readable result](live-results.json) preserves the measured timings, token counts, HTTP statuses, and fallback events without storing prompts or response bodies. Readiness requires resolving approved-model availability and distinguishing the Groq audit failure with safe structured diagnostics. Any further live verification requires new approval.
