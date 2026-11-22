# Stage 1.7C-FIX2 root-cause isolation

**Live readiness remains unverified.** No authenticated provider or generation requests were made. Historical reports, result files, and both consumed receipts were preserved.

## Groq

The normalized draft first goes through whole-draft claim validation and scoped completeness. The final response boundary then runs `model_weather_answer_is_grounded`, which splits text into clauses and independently checks named location, units, numeric coverage, and categorical weather assertions. The earlier live diagnostics establish a disagreement at this final gate. The original draft is unavailable, so the historical rejection cannot be reproduced exactly or assigned to a clause or evidence item.

Two mocked responses reproduce the disagreement without relying on a live model:

| Fixture example | Supported evidence | Exact first rejection |
|---|---|---|
| Correct 21 °C in Lisbon, followed by “In Lisbon it will be sunny tomorrow.” | `ev_obs_temp_current` supports the observed temperature. No forecast item supports the second clause. | Clause 2, `no_extractable_clause_claim`. The whole-draft numerical audit misses the additional categorical forecast. The final rejection is appropriate. |
| Correct Lisbon temperature and humidity joined by “and.” This variant adds an observed humidity field to the fixture. | `ev_obs_temp_current` and `ev_obs_humidity_current` support the values in the whole-draft audit. | Clause 2, `missing_clause_location`. The split drops the shared Lisbon scope before evidence lookup. This is conservative for natural compound wording. |

The new harness diagnostic calls the production gate and reports the first rejecting clause index, a fixed reason, bounded claim types and statuses, numeric counts when applicable, and supported synthetic-fixture evidence IDs. It stores no prose or unsupported values. No production behavior was changed. The known compound limitation does not establish that it caused the historical failure or that relaxing clause locality would be safe for mixed-city drafts.

## Gemini

The implementation uses the Google Developer API over HTTPS with `POST /v1beta/models/{bare-model-id}:generateContent`, API-key header authentication, and the documented text structure with `contents`, `systemInstruction`, and `generationConfig`. Source and mocked verification did not reveal a URL or payload defect.

Google currently documents `gemini-2.5-flash` as deprecated and says access to 2.5 models is limited to prior active users. This makes project/model eligibility a plausible explanation for the live `NOT_FOUND`, but the record cannot establish this project's eligibility or the precise historical cause. No adapter, model ID, or credential setting was changed. [GenerateContent contract](https://ai.google.dev/api/generate-content) · [Deprecation schedule and access notes](https://ai.google.dev/gemini-api/docs/deprecations#gemini-2.5-flash-models)

## OpenRouter

The adapter sends `POST /api/v1/chat/completions` with the exact allowlisted `qwen/qwen3-coder:free`, zero prompt and completion price ceilings, required parameter support, and provider fallback disabled. The **public endpoint metadata currently identifies that exact free variant and returns an empty endpoint list**. This confirms that the public metadata shows no serving route now. It supports a route-availability explanation for the 404, without proving availability at the time of either historical request. The similarly named paid variant is a distinct model. No allowlist or price setting was changed. [Public free-variant endpoint metadata](https://openrouter.ai/api/v1/models/qwen/qwen3-coder:free/endpoints)

## Offline verification

Only the Stage 1.7C evaluation diagnostics and tests were modified. All checks ran sequentially under verified 512 MiB soft, 768 MiB hard, and zero-swap cgroup limits.

| Check | Result | Peak |
|---|---:|---:|
| Focused gateway, fallback and diagnostic tests | 43 passed | 79.3 MiB |
| Backend suite | 343 passed | 88.4 MiB |
| Frozen 120-case evaluation | All gates passed | 40.9 MiB |

Frozen results were **101/120 complete**, **12/12 hazard coverage**, **7/8 both-city coverage**, **88/88 audited outputs grounded**, and **zero unaudited numerical weather answers**. No OOM events occurred. `git diff --check` passed.

## Smallest proposed live matrix, pending fresh approval

Run one Groq-only request against `openai/gpt-oss-120b` at the existing chat completions endpoint with the original Lisbon prompt and local 21 °C fixture. Retain the 350-token output cap and 224-token historical input estimate, no tools, no corrections, no retries, no redirects, and zero weather calls. Use a new single-use receipt and separate result file. This requires a Groq-only selector in the harness before execution. A new draft can identify its own rejecting clause and branch, while the historical draft remains unrecoverable.

Exclude Gemini and OpenRouter generation from this matrix. Revisit Gemini after separately authorized project-level model metadata confirms an eligible model. Revisit OpenRouter only after public metadata shows an eligible zero-price endpoint for an explicitly approved allowlisted model.
