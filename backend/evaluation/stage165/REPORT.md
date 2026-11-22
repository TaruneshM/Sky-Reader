# Stage 1.6.5 bounded live validation

**NOT READY — FIX REQUIRED.** One approved run completed with exit status 1. Six Open-Meteo-backed cases passed. The harness blocked the Groq request before dispatch, then stopped.

| Case | Exact user message | Expected check |
|---|---|---|
| Current | What's the weather in Tokyo, Japan right now? | Supported temperature and observed conditions |
| Tomorrow | Tomorrow's weather in Lisbon, Portugal? | Supported temperature, rain probability and wind for tomorrow |
| Umbrella | Will it rain in Singapore tonight, and should I bring an umbrella? | Supported rain probability and umbrella guidance |
| Safety | Is it safe to walk outdoors in Mumbai, India tomorrow? | Scoped risk assessment with every detected HIGH or SEVERE hazard |
| Comparison | Compare Paris, France and Berlin, Germany tomorrow. | Supported temperature, rain and wind for each city |
| Follow-up | How windy will it be there tomorrow? | Same Tokyo conversation scope, supported wind, correct anchor |
| Synthesis | Explain the wind forecast in Lisbon, Portugal tomorrow in detail. | Scoped wind evidence with the standard production audit and completeness check |
| Unsupported | What is the temperature in Tokyo, Japan next month? | Explicit limitation without numerical weather claims |

The harness uses the production agent, planner, auditors and request-scoped limits. The SDK client has zero retries and a 15-second request timeout. A shared wrapper checks the suite and case quotas immediately before dispatching any SDK request, including a correction. Seven cases have a zero-call allowance. The synthesis case can use two attempts, so the **planned maximum is two Groq calls** against a hard suite ceiling of two. An unexpected Groq route in a zero-call case is blocked before dispatch and reported as a failure. Cases are serial, with a 40-second case timeout. The fixed single-use receipt is reserved before dispatch and stays reserved even if the run fails or is cancelled.

Expect **about 13 Open-Meteo HTTP attempts** on success when the existing cache and state reuse work as expected. Allow up to **18 distinct lookups or forecast fetches** without reuse, and up to **36 attempts** under the current one-retry weather transport for these fixed cases. Provider responses and early stopping can reduce the count. Weather counts come from the production tracer. No forecast values are prewritten.

A local dotenv Groq key assignment was detected without displaying it. Credential validity and available quota are unverified. Mocked checks covered case and suite budget enforcement, cancellation and concurrent dispatch rejection, missing usage, safe error reporting, receipt reuse, and SQLite provider-failure revision behavior. The five-test capped batch passed with a **76.7 MiB** peak and zero OOM events. The live harness carries only synthetic in-memory conversation state. SQLite behavior was checked separately with the mocked regression. Numerical coverage and hazard checks complement production validation and do not constitute an independent meteorological judgment. If the live safety case has no material hazards, its hazard-coverage metric is unavailable.

## Command executed once

The following command was executed once from the repository root. The 360-second outer timeout covers eight serial cases of up to 40 seconds plus startup and reporting. Each shell verifies all three limits before launching Python. The runner independently verifies them again. The output includes per-case timings and checks, actual usage with missing counts, estimates, and cgroup peak memory. The wrapper prints the process exit code and final peak even if the runner times out.

```bash
systemd-run --user --scope --quiet \
  -p MemoryHigh=512M -p MemoryMax=768M -p MemorySwapMax=0 \
  /bin/bash -c '
    group=$(cut -d: -f3 /proc/self/cgroup)
    base="/sys/fs/cgroup$group"
    [[ $(cat "$base/memory.high") == 536870912 &&
       $(cat "$base/memory.max") == 805306368 &&
       $(cat "$base/memory.swap.max") == 0 ]] || exit 99
    PYTHONDONTWRITEBYTECODE=1 timeout -k 2s 360s \
      /home/victus/ml_env/bin/python -m backend.evaluation.stage165.runner --live \
      --approval-receipt backend/evaluation/stage165/live-run.used \
      --output backend/evaluation/stage165/live-results.json
    status=$?
    printf "exit=%s peak_bytes=%s\n" "$status" "$(cat "$base/memory.peak")"
    exit "$status"
  '
```

## Measured results

| Case | Outcome | End-to-end latency | Open-Meteo attempts | Groq HTTP attempts |
|---|---|---:|---:|---:|
| Current | Pass. Tokyo temperature and observed conditions validated. | 1,415.52 ms | 2 | 0 |
| Tomorrow | Pass. Lisbon temperature, rain probability and wind validated. | 1,590.82 ms | 2 | 0 |
| Umbrella | Pass. Singapore rain evidence and umbrella guidance covered. | 1,317.64 ms | 2 | 0 |
| Safety | Pass. Mumbai risk assessment validated. No HIGH or SEVERE hazard was detected, so live material-hazard coverage was untested. | 1,282.71 ms | 2 | 0 |
| Comparison | Pass. Paris and Berlin each had supported temperature, rain and wind. | 7,924.96 ms | 4 | 0 |
| Follow-up | Pass. Tokyo anchor retained and tomorrow's wind validated. | 545.34 ms | 1 | 0 |
| Synthesis | Blocked by the outbound allowlist. Agent category `groq_service_failure`. | 8.29 ms | 0 | 0 |
| Unsupported | Skipped after the outbound stop. | — | — | — |

The six successful responses passed evidence and completeness checks. The harness observed zero unsupported or unaudited numerical claims in those responses. The median elapsed time for the seven started cases was **1,317.64 ms**, including the locally blocked synthesis case. The cgroup's final peak was **50,651,136 bytes (48.3 MiB)**. The run verified **512 MiB soft, 768 MiB hard, and zero swap** before launching Python. It consumed 13 of 36 allowed Open-Meteo attempts and zero of two allowed Groq HTTP attempts.

One SDK invocation was charged against the case budget. The network transport rejected it before dispatch, so there was no Groq response, actual token telemetry, rate-limit response, or authentication response. The local pre-dispatch prompt estimate was 443 tokens. The estimate is not provider usage. The machine-readable [run record](live-results.json) distinguishes SDK invocations from outbound attempts.

## Root cause and readiness

The installed Groq SDK posts to `/openai/v1/chat/completions` relative to its configured base URL. The harness supplied a base URL already ending in `/openai/v1`, so the SDK assembled a duplicated path. The exact-path allowlist correctly blocked it and stopped the suite. The approval receipt remains consumed. The run was not repeated.

Before a newly approved live run, configure the Groq base URL at the HTTPS origin and add a mocked integration that passes the installed SDK's generated request through the exact transport allowlist. The existing offline checks verified the budget and allowlist independently and missed this integration boundary. The live Groq, unsupported-request, and material-hazard gates remain unverified. No production or frozen Stage 1.6.3 files were altered.

## Stage 1.6.5A separately approved retest

**Current recommendation — READY WITH LIMITATIONS.** The original run above remains the historical record. The fresh approval covered only the two cases below. The runner used `--retest`, wrote [a separate result file](retest-165a.json), and consumed `retest-165a.used` once. The original receipt and results were preserved.

Groq SDK 0.37.1 generated exactly `POST https://api.groq.com/openai/v1/chat/completions` with the corrected HTTPS origin in mocked verification. All ten harness tests passed under the capped scope. The exact allowlist remained active, redirects were disabled, and both SDK/transport retries and Open-Meteo application retries were disabled for this retest. The live run was sequential, with verified 512 MiB soft memory, 768 MiB hard memory, zero swap, a 40-second per-case timeout and a 95-second outer timeout.

| Case | Result | End-to-end latency | Open-Meteo HTTP | Groq HTTP | Actual input / output tokens |
|---|---|---:|---:|---:|---:|
| Lisbon wind synthesis | Pass. Scoped wind claims were audited and the answer passed completeness. | 4,873.46 ms | 2 | 2 | 1,386 / 1,140 |
| Tokyo next-month forecast | Pass. Explicit forecast-window limitation, no numerical prediction and no Groq invocation. | 1,316.35 ms | 2 | 0 | No calls |

Both Groq attempts completed and reported usage. The first reported 349 input and 466 output tokens, and the second reported 1,037 input and 674 output. The pre-call prompt estimate was 1,646 tokens across both calls. The retest observed zero unsupported or unaudited numerical claims, no provider error or rate-limit response, and no outbound guard stop. It used four of 36 allowed weather HTTP attempts and both allowed Groq attempts. Exit status was **0** and cgroup peak was **46,309,376 bytes (44.2 MiB)**.

The original six successes and these two retest successes cover the eight approved cases across two executions. They do not establish production latency, wider quota behavior or live HIGH/SEVERE hazard handling. The live safety case did not encounter a material hazard. The retest was not repeated.
