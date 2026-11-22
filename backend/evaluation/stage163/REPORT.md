# Sky Reader Stage 1.6.3 evaluation

Stage 1.6.2 answered **87 of 120 held-out cases completely (72.5%)** under controlled providers. It selected the deterministic path in 72 cases, including two whose needs called for clarification or qualitative synthesis. Three route-appropriate deterministic compound answers still omitted part of the request. The highest-priority issue is an unprepared agent path that can return measurement-shaped text with no weather evidence. Two safety cases stopped before reporting hazards present in the fixture.

## A. Dataset and method

The evaluation has 120 distinct messages, with ten each for simple weather, informal phrasing, geography, clarification, context, compound questions, city comparison, relative time, activity, safety, insufficient evidence, and complex requests. Thirty cases supply prior turns. Expected routing is 85 deterministic answers, 13 Groq-capable answers, nine clarifications and 13 evidence limitations. These are evaluation policy labels. They intentionally include behavior the repository does not yet support.

[Cases](cases.py) specify intent, destinations, forecast period, permitted route, provider fixture, prior turns, expected action and state transition, explicit qualifying countries where applicable, and answer requirements. Examples span accented and unaccented strings, similar spellings, all-empty candidates, same-name cities in Spain and Argentina, an incompatible country qualifier, and locations across several continents. Weather fixtures cover observations, two forecast days, local scope, two distinct sets of city readings, thunderstorms, rainfall, gusts, heat, fog, severe combinations, missing readings, contradictory WMO and precipitation signals, a truncated horizon, HTTP 503, timeout, and model quota. The forecast clock is fixed separately in each local fixture. Cross-country comparisons test local scope and separation under synthetic clocks with no claim of simultaneous real weather.

[Runner](run.py) uses the actual planner, agent, weather service, claim auditor and request-scoped tracer. It replaces outbound HTTP with an in-process transport and Groq with scripted replies. Prior turns use the same production agent with a fresh scope for each case. The report isolates the target turn after warm-up, including legitimate cache hits from previous turns. The harness runs sequentially.

Run from the repository root with its backend environment active.

```bash
PYTHONDONTWRITEBYTECODE=1 python -m backend.evaluation.stage163.run --output /tmp/stage163.json
```

The JSON includes per-case messages, responses, labels, resolved destinations, timings, provider counts, and prompt lengths. Scripted Groq behavior tests orchestration, rejection and fallback. It cannot measure the quality or stochastic behavior of the real model. The fixture distribution is balanced by evaluation category and cannot estimate production traffic proportions.

## Production execution paths

1. [API](../../main.py) validates the request and, for threaded calls, loads the owner-scoped SQLite context and checks the revision. It trims client transcript history before invoking the agent. [Conversation store](../../conversation_store.py) rechecks ownership, session validity and revision on write. The provider-error branch returns safe typed status metadata without a state write. Informational clarification or evidence-limitation responses can commit state.
2. [Router](../../agent/router.py) extracts one primary intent, destination hints, activity, comparison markers and time. [Shared planner](../../agent/request_planner.py) prefers trusted state to transcript hints. It can fill a pending slot, apply location qualifiers, open a new task or reuse a confirmed anchor. The [state transitions](../../agent/conversation_state.py) bind each operation to scope and task. Typed geocoding distinguishes resolved, ambiguous, missing and provider-unavailable outcomes. The planner resolves each slot, scopes forecast locally and retains confirmed coordinates and window provenance. It exits early for missing locations, missing comparison pairs, safety comparisons, ambiguity and relative comparisons without a target time.
3. [Agent](../../agent/agent.py) handles prepared relative comparisons, prepared singles and prepared pairs separately. Single answers assemble measurements and risk findings, then run [completeness requirements](../../agent/answer_completeness.py) plus the claim audit. Pair answers bind each city's evidence to its forecast window and coordinates. Incomplete evidence can return a bounded advisory. Some detailed requests with a material hazard take a bounded deterministic branch. Injected historical executors have a separate legacy branch.
4. Remaining prepared requests can enter the Groq loop. The initial prompt includes planner data, location metadata, recent transcript and full tool schemas. The loop can serve prepared results without another weather fetch. It accumulates prior turns and tool replies, uses complexity-based completion limits of 350, 650 or 1,200 tokens, and allows up to ten iterations by default. It may run one factual correction. A complete prepared comparison can survive provider failure. A complex request with no eligible fallback preserves the typed failure. An unprepared request can also reach the loop. The guard before the no-tools response relies on the agent's narrower weather-topic detection.
5. The [evidence controller](../../evidence/hallucination_controller.py) extracts claims and validates them against each source before report and proof construction. Completeness asks whether required supported claims and guidance are present. After correction or fallback, the outgoing text is audited again where evidence is supplied. [Tracing](../../agent/tracer.py) records request-level calls, token availability, fallback, timings and provider attempts. Groq SDK retries are disabled. The weather transport retries transient connection and timeout failures once.

## B. Generalization and routing

| Expected / observed | Deterministic | Groq attempted | Clarification | Limitation |
|---|---:|---:|---:|---:|
| Deterministic | 70 | 4 | 11 | 0 |
| Groq permitted | 1 | 9 | 3 | 0 |
| Clarification | 1 | 9 | 0 | 8 | 0 |
| Limitation | 0 | 2 | 3 | 8 |

Observed routing uses precedence of Groq attempted, deterministic selected, planner clarification, and limitation. A deterministic fallback after a quota attempt therefore appears in the Groq column. Deterministic routing precision was **70/72 (97.2%)** and recall was **70/85 (82.4%)**. Six requests attempted Groq outside the permitted class. Seven weather-labeled requests attempted it without a prepared destination, including some requests where Groq was permitted only after preparation.

| Measure | Pass |
|---|---:|
| Primary intent label | 105/120 |
| Parsed destination, among cases with named expected destinations | 91/111 |
| Resolved destination or correct absence, including explicit qualifying country | 93/120 |
| Planner forecast-window label | 117/120 |
| Expected state transition | 95/120 |
| Clarification-category state and answer | 10/10 |
| Expected behavior, including allowed typed failures and fallbacks | 88/120 |

Window score compares the selected period label even when location resolution prevents fetching. Answer text names the expected location in 81/97 and period in 80/97 weather-answer cases. Routing and state checks distinguish accepted aliases from corrupted extracted names. The scripted empty candidate for unqualified `Lisbn`, tied Córdoba rows, truncated forecasts, weather timeout and weather 503 are provider/fixture limits. The `right`, `Zürich pls` and `Accra and how humid` queries are parser faults even though they subsequently return location-not-found.

## C. Answer quality and safety

Completeness requires the case's explicit measurements, uncertainty/clarification terms or recommendation content, expected state, and, for expected weather answers, correct place/window and no failed numeric or claim check. A listed hazard must appear. Caution is credited for specific language such as postponement, shelter or slowing down and rejected for unqualified positive safety wording. These text criteria are reproducible proxies for intent and appropriateness. They can miss valid paraphrases or subtleties such as negated hazard mentions. Independent numeric checks use fixture values and expected scope. For city pairs, each city's distinct temperature, rain and wind must occur on its own line. The independent literal checker cannot fully validate explanations, units beyond the fixture vocabulary, or subtle qualitative implications.

| Measure | Pass |
|---|---:|
| Independent completeness including expected clarifications and limitations | 87/120 |
| Complete weather answers, among 97 expected answers with places | 70/97 |
| Application audit for outputs with extracted claims | 78/78 |
| Independent numeric-and-scope checks for outputs with recognized literals | 74/75 |
| Both-city temperature, precipitation and wind in correct city scope | 4/8 |
| Required hazards and caution | 10/12 |
| Activity-category completeness | 8/10 |
| Complex-category completeness | 2/10 |
| Compound-category completeness | 4/10 |

The single independent numeric-scope failure was a valid Cebu observation given in place of a cross-place clarification. It illustrates the difference between numeric accuracy and answering the question. The 78/78 claim audit denominator excludes replies without extracted claims, including an unaudited numerical Groq draft in the hourly-breakdown reproduction. The report credits retained thunderstorms under incomplete rainfall/temperature evidence, a storm code despite zero reported rainfall, distinct severe gust and thunderstorm signals, heat and fog caution. Two hazard failures were omissions before weather preparation, with no observed positive safety recommendation in those two cases. Both injected weather transport failures remained typed, and the two quota cases produced one complete comparison fallback and one typed quota failure.

## D. Controlled efficiency and usage

| Category | Complete / 10 | Deterministic selected | Groq attempted / completed / failed | Synthetic prompt / completion tokens | Estimated missing tokens | Weather HTTP |
|---|---:|---:|---:|---:|---:|---:|
| Simple | 9 | 9 | 0 / 0 / 0 | — | — | 19 |
| Informal | 7 | 7 | 0 / 0 / 0 | — | — | 15 |
| Geography | 10 | 7 | 0 / 0 / 0 | — | — | 17 |
| Clarification | 10 | 9 | 1 / 1 / 0 | 412 / 37 | — | 18 |
| Context | 8 | 7 | 0 / 0 / 0 | — | — | 11 |
| Compound | 4 | 7 | 1 / 1 / 0 | 412 / 37 | — | 14 |
| Comparison | 6 | 3 | 2 / 1 / 1 | 412 / 37 | 2,206 | 21 |
| Relative | 7 | 6 | 0 / 0 / 0 | — | — | 11 |
| Activity | 8 | 8 | 2 / 2 / 0 | 824 / 74 | — | 16 |
| Safety | 8 | 8 | 0 / 0 / 0 | — | — | 16 |
| Insufficient | 8 | 1 | 0 / 0 / 0 | — | — | 19 |
| Complex | 2 | 0 | 14 / 13 / 1 | 4,944 / 444 | 3,716 | 10 |
| **Total** | **87** | 72 | **20 / 18 / 2** | **7,004 / 629** | **5,922** | **187** |

The model usage average was **0.167 attempts per target turn** with 15 client constructions. No deterministic-selected turn constructed a client. The mock returned a fixed 412 prompt and 37 completion tokens on 17 calls. The remaining three attempts lacked metadata. Their estimates use one token per four serialized input/output characters, rounded up. Failed attempts have only a prompt-size estimate. An em dash denotes no applicable recorded values or estimates. **Actual provider token consumption was not measured.**

There were 97 geocoding and 90 weather-data HTTP attempts, including retries, or 1.56 per target turn. One correction ran in the complex category. There were 115 responses with one reported iteration and two with three, with iteration counts absent for three typed failures. The returned iteration count includes deterministic responses. Both three-round trials reused the same single prepared forecast without additional weather calls. In those trials serialized calls grew from **8,541 → 9,845 → 11,149** and **7,909 → 8,599 → 9,289** characters. Full tool schemas accounted for **3,929 characters per ordinary Groq round**. The single correction request was 6,226 characters and omitted tool schemas.

Latency below uses 70 complete weather answers only, excludes setup and uses fixed 2 ms weather and 8 ms Groq mock delays. Mock weather retry backoff is compressed. Planner includes provider waits, and audit time includes all instrumented audit invocations, so these rows are not additive.

| Measured span | Median ms | p95 ms | n |
|---|---:|---:|---:|
| Total agent request | 6.65 | 15.67 | 70 |
| Planner | 5.58 | 10.85 | 70 |
| Weather HTTP attempts | 4.95 | 9.73 | 70 |
| Evidence audit | 0.29 | 0.83 | 70 |
| Complete weather answers without Groq | 6.62 | 12.29 | 67 |
| Complete weather answers with Groq | 23.06 | — | 3 |
| Groq duration on those complete answers | 8.70 | — | 3 |

These are mocked path costs, not live latency or a matched treatment comparison between the two groups. The three successful Groq cases are too few for a useful tail estimate. Errors and clarifications were excluded from success latency.

## E. Significant failures

| Severity | Reproduction | Root cause and proposed fix |
|---|---|---|
| High, unsupported facts | `Could you give an hourly breakdown for Lyon tomorrow?` | The router extracts Lyon and tomorrow, but the shared planner finds no supported intent or recognized weather keyword and returns without preparing evidence. The agent fallback also misses `hourly breakdown`. With no tools or prepared sources, a scripted numerical forecast was returned without audit. Gate weather-shaped answers on prepared sources and reject unsupported factual drafts. [Router](../../agent/router.py) · [Agent](../../agent/agent.py) |
| High, hazard omitted | `What are the hazards for hiking in Suva tomorrow?` | `explicit_location` accepts the outer `for hiking in Suva` match and the provider correctly has no such city. Prefer the location-bearing nested phrase and preserve hazard intent while resolving it. [Router](../../agent/router.py) |
| High, safety comparison declined | `Compare safety in Muscat and Suva tonight.` | The planner's explicit safety-comparison branch asks which city to assess first before fetching forecasts. That is a conservative refusal, but it omits both known fixture hazards for an explicit two-city request. Add a scoped dual-city safety summary, with uncertainty and destination-specific guidance. [Planner](../../agent/request_planner.py) |
| Medium, false completeness | `Give the temperature and risk of rain in Recife tonight.` | Intent priority selects temperature and the secondary completeness vocabulary misses `risk of rain`, so the audited temperature alone passes. Preserve all requested measurements and scope rain wording independently of hazard intent. [Completeness](../../agent/answer_completeness.py) |
| Medium, wrong window and incomplete answer | `Will it rain and get windy after sunset?` | The router misses sunset, defaults the prepared rain window to the next 24 hours and drops the wind request. Resolve to a defined local window when supported or clarify before computing peaks. [Router](../../agent/router.py) · [Planner](../../agent/request_planner.py) |
| Medium, wrong comparison target | `Is it colder than the place we checked earlier?` | Relative parsing only recognizes a supported time after `than`, then ordinary context inheritance promotes the latest city to a single-site observation. Use a comparison operand type and resolve the earlier destination or ask which place. [Router](../../agent/router.py) |
| Medium, parsing and activity gaps | `soo weather about Zürich pls?`, `Can I go hiking in Cebu tomorrow morning?` | Informal suffixes enter geocoder queries and verb patterns miss some inflections or multiword activity phrases. Add held-out grammar patterns and conservative candidate boundaries. [Router](../../agent/router.py) |
| Medium, unnecessary loop and clarification | `Explain the wind forecast in Lisbon tomorrow in detail.` | The primary route treats the request as general forecast, requests broader output than the specified wind topic, and permits cached tool replies to repeat. Narrow obligations and suppress redundant tool rounds. [Router](../../agent/router.py) · [Agent](../../agent/agent.py) |

The 1.6.3 work makes no production fixes. In particular, upstream data outages and geocoding misses were left as distinct findings.

## F. Priorities for Stage 1.6.4

1. **Block unsupported weather answers.** Require prepared or independently validated evidence for every weather-shaped answer, including unclassified hourly and trip wording. Add the safety reproductions as explicit release gates. Preserve the existing transcript and revision rules for provider failures.
2. **Represent the requested work explicitly.** Track multiple measurements, time anchors, activity, and comparison operands separately. Expand parsing on a new holdout, including informal endings, nested prepositions, relative places, and time ranges. Use distinct error/clarification reasons for parse errors, unsupported periods and provider limits.
3. **Choose a synthesis mode before constructing a client.** Serve deterministic eligible cases as today, include a focused synthesis-only mode for prepared evidence, and expose only tools whose results are still needed. The two repeat-tool mock cases show prompt growth without new observations.
4. **Compact prepared prompts and context.** Pass one versioned structured evidence block. Repeated tool calls can refer to that block by scope rather than reattach data. The last-four transcript policy retains indiscriminate text even when trusted state already carries location, time, and activity. Filter to unresolved context and measure prompt byte and token growth. Benchmark whether compact prompts actually preserve completeness.
5. **Budget the entire request and bound recovery.** Cap tokens across synthesis, any tool rounds and correction. Stop repeated tools with no evidence gain. For correction, target the failed claim or fall back when complete deterministic evidence exists. Retain typed throttle, quota and timeout semantics and the SDK's zero-retry policy until measured data justifies a bounded retry strategy. Capture retry behavior and distinguish real usage, estimates and unknowns in reporting.

## G. Production measurement, isolation and verification

The repository contains the metrics logger and trace schema, but no accessible production telemetry export was found. No keys or private conversation data were read for this evaluation. No live Groq or Open-Meteo calls were made. An approved redacted metrics export should come first. Useful fields are attempted/completed calls, known actual usage, failure category, fallback, route, tool and provider counts, timings, and a rotating non-identifying grouping key. Actual prompt/completion totals, cache behavior at real traffic levels, concurrency, provider percentiles, and live model quality remain unmeasured.

If approved later, use six synthetic live cases covering a zero-call control, prepared wind detail, both-city trade-off, uncertainty follow-up, cycling advice and a complex weather itinerary. Use the backend entry point with a two-round app cap and at most one correction per case, a client-side hard cap of 18 requests for the sample, and no retries. The observed mock prompt sizes imply a planning budget of about **54,000 input tokens** at 3,000 per call and at most **21,600 completion tokens** at 1,200 per call. Input estimates need a preflight token counter and budget enforcement. Actual billed tokens require provider usage metadata. Ask for explicit approval for this quota-consuming execution after reviewing the export and questions.

The offline regression suite passed **265 backend tests** and **20 frontend tests**. Frontend build, lint and `git diff --check` passed. Temporary SQLite integration tests exercised ownership, guest credential isolation and revocation, revision conflicts, new-thread isolation, clear behavior, expiry/logout during in-flight writes and state preservation after provider errors. Frontend tests covered New Chat, Clear History, account switches and absence of assistant error pollution. Weather/evidence tests and the held-out pair checks exercised provenance isolation. Existing redaction tests cover synthetic upstream secrets and diagnostic fields. There was no full browser session against a live server in this milestone.

No production or frozen Phase 7 files were changed by Stage 1.6.3. The existing worktree changes from earlier stages were retained.
