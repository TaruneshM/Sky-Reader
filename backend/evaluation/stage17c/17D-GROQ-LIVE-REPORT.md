# Stage 1.7D Groq-only live validation

**Passed directly.** The single approved request used `openai/gpt-oss-120b` and the original fixed Lisbon current-temperature observation. The draft passed the final evidence gate. The agent delivered the original synthesis without invoking limited deterministic recovery.

| Check | Result |
|---|---|
| HTTP status | 200 |
| Case / provider attempt latency | 1,129.95 ms / 1,121.25 ms |
| Actual usage | 264 input, 219 output, 483 total tokens |
| Finish reason | `stop`. No truncation indicated. Output remained below 350 tokens. |
| Draft grounding | Whole-draft audit and final evidence gate both passed |
| Final delivered-answer grounding | Passed. Temperature `SUPPORTED` by the Lisbon observation ID. |
| Final delivered-answer completeness | Passed |
| Deterministic recovery / limited answer | Neither occurred |
| Process exit and peak cgroup memory | Exit 0, 42,987,520 bytes (41.0 MiB), zero OOM events |

The 21-test mocked preflight passed under the same verified 512 MiB soft, 768 MiB hard and zero-swap limits. The live run verifies direct delivery for one model sample. It did not exercise the live recovery branch, which remains covered by mocked tests. No Gemini, OpenRouter, or weather requests were made. There were no retries, redirects, corrections, or provider fallback.

The [sanitized result](17d-groq-results.json) and fresh consumed receipt are separate from the historical records. No full draft, prompt or credentials were stored. Production validation and frozen evaluation artifacts were unchanged during the run.
