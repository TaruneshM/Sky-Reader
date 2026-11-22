# Stage 1.7C diagnostic retest

**NOT READY — FIX REQUIRED.** The separately approved matrix ran once. All three requests reached their approved live endpoints. No case passed the end-to-end acceptance check.

| Live provider and model | HTTP result | Case latency | Actual input / output tokens | Diagnostic |
|---|---:|---:|---:|---|
| Groq `openai/gpt-oss-120b` | 200 | 1,272.27 ms | 224 / 296 | Draft audit passed. The final model evidence gate rejected the draft. |
| Gemini `gemini-2.5-flash` | 404 | 498.76 ms | Unknown / unknown | `NOT_FOUND`. Sanitized summary reports a missing resource or endpoint. |
| OpenRouter `qwen/qwen3-coder:free` | 404 | 613.37 ms | Unknown / unknown | Numeric code `404`. Sanitized summary reports a missing resource or endpoint. |

The Groq draft had no missing temperature requirements or unsupported extracted claim types. It included the expected location and temperature units. The normalized finish reason was `stop`, with no truncation indicated, and reported usage stayed below the 350-token output cap. The final evidence gate returned false and withheld the draft. This localizes the failure to the final gate, but the recorded diagnostics do not identify the exact clause or whether rejecting it was correct. The final answer's audit and completeness flags were both false.

The Gemini case injected Groq 429 locally. The OpenRouter case injected Groq 429 and Gemini 503 locally. The expected provider transitions occurred. Neither live 404 was classified as retryable or eligible for further fallback. The sanitized summaries do not distinguish model availability from endpoint or routing conditions.

There were three outbound requests total and zero weather calls. No retries, redirects, or substitutions occurred. OpenRouter retained the exact free-model allowlist, both zero-price ceilings, and provider-side fallback disabled. The run exited **1** and reached **43,479,040 bytes (41.5 MiB)** peak cgroup memory, with zero OOM events. The offline preflight passed eight tests under the verified memory limits.

The [sanitized result](diagnostic-results.json) is separate from the original [live record](live-results.json) and [corrective report](FIX-REPORT.md). Both approval receipts remain consumed. No raw response drafts, credential values, headers, or full provider error bodies were saved. No further live requests were attempted.
