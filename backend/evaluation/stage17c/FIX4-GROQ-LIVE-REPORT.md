# Stage 1.7C-FIX4 Groq-only diagnostic

**Validation failed.** The single approved `openai/gpt-oss-120b` request used the original fixed Lisbon fixture. No other provider or weather endpoints were contacted.

| Measure | Result |
|---|---|
| HTTP status | 200 |
| End-to-end / provider attempt latency | 1,237.11 ms / 1,228.46 ms |
| Actual input / output tokens | 224 / 257, 481 total |
| Finish reason | `stop`. No truncation indicated. |
| Whole-draft audit | Passed. Two extracted temperature claims were `SUPPORTED`, each by `ev_obs_temp_current`. |
| Draft completeness | No missing requirements reported. |
| Final gate | Failed at clause **3** with `missing_clause_location`. |
| First failed prerequisite | `previous_location_anchor_required` |
| Rejected clause audit | No claim statuses or evidence IDs. The location gate rejected the clause before claim auditing. |
| Final grounding and completeness | Both failed. The draft was withheld. |
| Exit and cgroup peak | Exit 1, 43,245,568 bytes (41.2 MiB), zero OOM events. |

There was one candidate location from observation-only evidence. Clause 3 contained no explicit match to it. The previous clause was not audited, so it had not been validated and no location anchor remained. Clause 3 independently did not match the permitted numeric continuation grammar and had no recognized forecast wording. The gate entered the inheritance decision, but did not apply a location. The draft was not retained, so the record does not establish what clause 2 said, why it did not require auditing, or whether clause 3 otherwise contained a supportable claim. This result pertains to the new response, which failed at clause 3 rather than the historical clause 2.

The preflight passed 35 mocked tests. The run verified 512 MiB soft, 768 MiB hard, and zero-swap memory limits. No retries, redirects, corrections or fallback occurred. The [sanitized output](fix4-groq-results.json) and fresh consumed receipt are separate from the historical artifacts. No validator changes were made during the run, and no draft, prompt, credentials, or sensitive provider payload was saved.
