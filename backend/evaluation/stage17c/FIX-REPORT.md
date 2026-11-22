# Stage 1.7C-FIX corrective report

**Live readiness remains unverified.** This milestone repairs the evaluation's diagnostic gaps. It does not establish a provider compatibility defect or change production routing. No provider API calls were made. The [original report](REPORT.md), [live artifact](live-results.json), and consumed receipt remain unchanged.

## Findings

| Provider | Confirmed | Unresolved |
|---|---|---|
| Groq | The approved request returned HTTP 200 and normalized successfully. It reported 224 input and 191 output tokens. The final evidence and completeness flags were false. | The draft, pre-fallback claim audit and finish reason were never saved. We cannot tell whether temperature, units, location, or another requirement was missing or unsupported. The reported 191 output tokens were below the 350 cap, which gives no direct evidence of truncation. It cannot establish the finish reason. |
| Gemini | The request reached the exact allowed HTTPS endpoint and returned 404. The adapter constructs `POST /v1beta/models/{bare-id}:generateContent`, sends the key in the API header, and uses `contents`, `systemInstruction` and `generationConfig.maxOutputTokens` for this text-only case. These match the documented REST shape. | Model availability for the configured API version or project is a possibility. The empty historical diagnostic cannot distinguish it from another missing resource or an intermediary response. The reviewed code provides no basis to change the endpoint, API version, payload or model. |
| OpenRouter | The allowed `POST /api/v1/chat/completions` reached HTTP 404. The request specified one allowlisted `:free` model, required parameter support, set zero prompt and completion price ceilings, and disabled provider fallback. | A missing model and no eligible free route under those constraints are distinct possibilities. The historical payload was not captured, so neither can be assigned as the root cause. The allowlist and pricing constraints remain in place. |

The reference contracts were checked against [Google GenerateContent](https://ai.google.dev/api/generate-content), [Google troubleshooting](https://ai.google.dev/gemini-api/docs/troubleshooting), [OpenRouter errors](https://openrouter.ai/docs/api/reference/errors-and-debugging), and [OpenRouter provider routing](https://openrouter.ai/docs/guides/routing/provider-selection).

The original Lisbon case uses a synthetic current reading of 21 °C. The agent requires supported temperature evidence. The harness also checks the exact fixture value, successful provider, completeness flag and zero weather calls. The final audit may describe a limitation rather than the original draft. The runner now separately checks the transient draft against the production auditor, completeness requirements and model evidence gate, without changing the actual agent decision.

## Changes

- [diagnostics.py](diagnostics.py) retains a diagnostic endpoint identifier, provider, configured model, HTTP status, recognized code/type, and a fixed sanitized message. Unknown provider codes and raw messages are never copied. It records transport retry eligibility and whether fallback is allowed for the final live target.
- [runner.py](runner.py) reads at most 2 KiB of uncompressed error content in the evaluation transport and discards it after classification. The adapter receives the original status and bounded numeric Retry-After where present, without unrestricted provider text. A harness-only observer records missing requirements, unsupported claim variables and statuses, location and unit markers, model evidence gate outcome, finish reason, and cap indicators. It persists no raw drafts or unsupported values.
- [test_stage17c.py](../../tests/test_stage17c.py) exercises representative Gemini and OpenRouter 404 envelopes, nested/free-form credential redaction, oversized error input, and missing/unsupported/truncated draft diagnostics. These are synthetic reproductions of diagnostic gaps. They do not identify the causes of the historical responses.

## Offline verification

| Check | Result | Peak cgroup memory |
|---|---:|---:|
| Harness and diagnostic tests | 8 passed | 76.3 MiB |
| Gateway and fallback | 33 passed | 77.1 MiB |
| Evidence and completeness | 40 passed | 74.9 MiB |
| Backend suite | 341 passed | 87.4 MiB |
| Frozen 120-case evaluation | All gates passed | 40.8 MiB |

The frozen evaluation retained **101/120 completeness**, **12/12 hazard coverage**, **7/8 both-city coverage**, **88/88 grounded audited outputs**, and **zero unaudited numerical answers**. All checks ran sequentially under verified 512 MiB soft, 768 MiB hard and zero-swap limits. There were no OOM events. The frozen artifacts and original Stage 1.7C artifacts were verified unchanged. `git diff --check` passed.

## Proposed next measurement, pending fresh approval

A three-request diagnostic retest is justified because the original response contents and finish reason cannot be recovered offline. Use a fresh receipt and separate results file. Preserve the exact original matrix and prompt, “Explain the current temperature in Lisbon, Portugal.” Use the original HTTPS POST endpoints, zero weather API calls, 350 maximum output tokens per dispatch, and no retries, redirects, corrections, substitutions or paid OpenRouter usage.

| Request | Model and endpoint | Purpose and estimated usage |
|---|---|---|
| One Groq request | `openai/gpt-oss-120b` at `https://api.groq.com/openai/v1/chat/completions` | Expect roughly 224 input tokens based on the prior fixture. Prior output was 191, with a hard cap of 350. Identify the missing or unsupported criteria and distinguish truncation from another failure. |
| One Gemini request after injected Groq 429 | `gemini-2.5-flash` at `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent` | Input roughly a few hundred tokens, provider tokenization unmeasured. Output capped at 350. Capture a safe code and diagnostic classification if rejected. |
| One OpenRouter request after injected Groq 429 and Gemini 503 | `qwen/qwen3-coder:free` at `https://openrouter.ai/api/v1/chat/completions` | Input roughly a few hundred tokens, provider tokenization unmeasured. Output capped at 350. Differentiate a reported route constraint from a reported missing model where possible. Both price ceilings stay zero. |

The exact statuses and usage are unknown until dispatch. The original approval remains consumed.
