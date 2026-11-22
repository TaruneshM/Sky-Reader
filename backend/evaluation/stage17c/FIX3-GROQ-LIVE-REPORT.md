# Stage 1.7C-FIX3 Groq-only live retest

**Validation failed.** One approved request used `openai/gpt-oss-120b` and the original synthetic Lisbon fixture. The context-aware production evidence gate withheld the draft.

| Measure | Result |
|---|---|
| HTTP status | 200 |
| End-to-end latency | 868.33 ms |
| Provider attempt latency | 858.94 ms |
| Actual tokens | 224 input, 141 output, 365 total |
| Finish reason | `stop`. No truncation indicated. Output stayed below the 350-token cap. |
| Whole-draft audit | Passed |
| Draft claim validation | Temperature `SUPPORTED`, evidence `ev_obs_temp_current`. No unsupported extracted claims. |
| Draft completeness | No missing requirements in the diagnostic audit |
| First final-gate rejection | Clause 2, `missing_clause_location` |
| Rejected clause claim statuses | None. Location rejection occurred before clause claim validation. |
| Final grounding and completeness | Both failed. The draft was withheld. |
| Process exit and peak | Exit 1, 42,803,200 bytes (40.8 MiB), zero OOM events |

The draft included Lisbon and temperature units, but clause 2 did not satisfy the final gate's explicit-location or safe-inheritance requirements. The sanitized diagnostics do not retain clause text or identify which inheritance prerequisite failed. This run reproduces the location rejection without truncation. It does not establish the cause of any historical draft's rejection.

The 27-test mocked preflight passed. The live run used verified 512 MiB soft, 768 MiB hard, and zero-swap limits. No Gemini, OpenRouter, or weather requests were made. No fallback, redirects, retries, or corrections occurred. The validator and budgets were unchanged during this run. The [sanitized results](fix3-groq-results.json) and fresh consumed receipt are separate from historical results and receipts. No draft or credentials were stored.
