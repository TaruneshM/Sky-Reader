# Stage 1.7C-FIX4 clause location diagnostics

No live calls were made. The latest historical run proves that clause 2 failed the location check before its claim audit. The draft was never retained. That record cannot establish whether the clause was numeric, introduced a place, or failed the preceding-anchor rule.

## Decision path

1. The gate splits on sentence punctuation followed by whitespace, newlines, semicolons, and designated conjunctions. It decides whether the resulting clause requires an audit. A nonempty skipped clause clears the anchor.
2. Explicit recognition matches a complete location label present in available evidence, with case-insensitive word boundaries. It does not geocode a draft or treat an unknown place name as evidence. Existing claim validation still rejects ambiguous location scope.
3. Inheritance requires exclusively observed evidence for exactly one city. The previous validated clause must establish or carry an eligible anchor. To establish one, its original wording must use the observed-location prefix and a supported numeric measurement in the existing grammar.
4. The new clause must match the simple numeric continuation grammar in full, without new place names or forecast wording. Location then enters the clause audit as verified context. Units, numerical claims, categorical assertions, and safety assurances still undergo the existing gate and audit. A successfully inherited location can carry to the next adjacent validated continuation.

Punctuation and conjunction splitting separate the location prefix from later clauses. Mocked cases confirm this behavior, including a simple compound that passes through the existing inheritance rule and a mixed observation/forecast case that cannot inherit. There was no confirmed segmentation defect attributable to the historical response. The parser and acceptance rules were left unchanged.

## New diagnostics

[The final gate](../../agent/weather_evidence_gate.py) now records the number of candidate evidence locations, whether the clause explicitly matches any of them, the number of explicit matches, whether the prior clause was validated, whether it established or carried an anchor, and the prior anchor status. It separately records evidence scope and a forecast-wording marker, numeric grammar eligibility, whether the gate entered the inheritance branch, and whether an anchor was applied before claim auditing.

| Failed prerequisite code | Meaning |
|---|---|
| `no_evidence_location` | No evidence location was available for matching. |
| `multiple_evidence_locations` | Candidate locations are not unique. |
| `observation_only_evidence_required` | Evidence includes a forecast or derived item, or is not observation-only. |
| `previous_location_anchor_required` | No eligible preceding anchor. Prior anchor status distinguishes a grammar mismatch, a skipped clause, no previous clause, and an ineligible evidence scope. |
| `numeric_continuation_required` | An anchor existed, but the new clause did not match the permitted numeric continuation form. |
| `grounded_claims_required` or `extractable_claim_required` | A clause reached claim auditing but failed to ground a claim or produced no extractable claim. |

Other rejecting branches retain their existing reasons and report fixed prerequisites for evidence, units, qualifications, numeric coverage, or categorical coverage. No clause text, place strings extracted from the draft, values, or prompts are added to the diagnostic.

[Tests](../../tests/test_clause_context.py) cover valid numeric continuations, conjunction splits, nonnumeric continuations, forecasts, mixed evidence, multiple cities, ambiguous references, new locations, and inherited claims that remain unsupported or contradicted. The new tests also show that a valid sentence naming Lisbon can fail to establish an anchor when its word order is outside the prefix grammar.

## Verification and next action

The focused batch passed **52 tests** and peaked at **75.8 MiB**. The backend suite passed **368 tests** and peaked at **88.8 MiB**. The frozen 120-case evaluation peaked at **41.3 MiB** and retained **101/120 completeness, 12/12 hazard coverage, 7/8 both-city coverage, 88/88 grounded audited outputs, and zero unaudited numerical answers**. All checks ran sequentially under verified 512 MiB soft, 768 MiB hard, and zero-swap limits. No OOM events occurred. Historical live results and receipts were unchanged. `git diff --check` passed.

If more live evidence is needed, the smallest proposed check is one separately approved Groq-only request using the original Lisbon fixture and 350-token cap, with a fresh receipt and existing outbound restrictions. The new fields can explain that response's decision. They cannot recover the earlier clause. Keep the acceptance rules in place until a specific supported construction is reproduced and its safety established.
