# Stage 1.7C-FIX2 Groq-only diagnostic

**The request reached Groq, but the final evidence gate withheld the draft.** One request used `openai/gpt-oss-120b` and the original synthetic Lisbon observation. There were no other provider requests, weather calls, fallback, retries, redirects, or corrections.

| Measure | Result |
|---|---|
| HTTP status | 200 |
| Case latency / provider attempt latency | 1,435.03 ms / 1,427.03 ms |
| Actual usage | 224 input, 350 output, 574 total tokens |
| Finish reason | `length`. Truncated at the approved 350-token cap. |
| Whole-draft audit | Passed, no unsupported extracted claims |
| Draft completeness requirements | None missing |
| Supporting fixture evidence | `ev_obs_temp_current` |
| First final-gate rejection | Clause 2, `missing_clause_location` |
| Clause-level claim statuses | None. The location check rejected the clause before its claim audit. |
| Final response | Audit and completeness checks did not pass. The draft was withheld. |

The full draft had a location and temperature units. The second clause did not explicitly name a location found in the evidence. The run records both truncation and the location rejection. It does not establish that truncation caused the rejection or that the clause was otherwise safe. The raw draft was not stored. This result does not retroactively identify the rejecting clause in the earlier live response.

The new Groq-only selector passed the 11-test offline preflight under verified 512 MiB soft, 768 MiB hard, and zero-swap limits. The live process exited **1** with a **43,642,880-byte (41.6 MiB)** peak and zero OOM events. The [sanitized result](fix2-groq-results.json) and fresh consumed receipt are separate from all historical records. The production evidence gate was unchanged. No retry was attempted.
