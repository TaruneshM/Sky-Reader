"""Conservative final check of factual weather clauses in model-drafted text."""
import re


WEATHER_TERMS = re.compile(
    r"\b(?:weather|forecast|temperatures?|humidity|humid|wind(?:s|y)?|gusts?|rain(?:s|y|fall|ing)?|"
    r"precipitation|showers?|thunder(?:storms?)?|lightning|storms?|snow(?:y|fall)?|hail|fog(?:gy)?|"
    r"visibility|sk(?:y|ies)|cloud(?:s|y|iness)?|overcast|pour(?:ing)?|flurries|clear sk(?:y|ies)|sunny|sleet|freezing|heat index|"
    r"drizzle|dewp?oint|wind chill|flood(?:ing)?|cyclones?|hurricanes?|tornado(?:es)?|"
    r"risk(?: level)?|hazards?|(?:unsafe|safe) to (?:walk|drive|travel|hike|cycle|go|exercise))\b",
    re.I,
)
MEASUREMENT = re.compile(
    r"(?<!\w)[−-]?\d+(?:[.,]\d+)?\s*(?:°\s*[CFK]?|degrees?\b|celsius\b|fahrenheit\b|km\s*/\s*h\b|"
    r"mph\b|kph\b|m\s*/\s*s\b|knots?\b|mm\b|hpa\b|%)", re.I
)
NUMBER = re.compile(r"(?<![\w−-])[−-]?\d+(?:\.\d+)?")
UNSUPPORTED_UNIT = re.compile(r"\d\s*(?:°\s*f\b|mph\b|kph\b|knots?\b|m\s*/\s*s\b)", re.I)
TIMED_ASSERTION = re.compile(
    r"\b(?:tonight|tomorrow|today|this (?:evening|morning|afternoon)|currently|overnight)\b"
    r"[^.!?]*?\b(?:will|is|are|be|reach|hit|drop)\b", re.I,
)
UNSAFE_CERTAINTY = re.compile(
    r"\b(?:guaranteed|definitely|no risk|safe to|no precautions needed|will not rain|won['’]t rain)\b", re.I,
)
CONDITION_FRAGMENT = re.compile(
    r"\b(?:detected hazards?|clear sk(?:y|ies)|sunny|overcast|cloudy|thunderstorms?|reduced visibility|"
    r"severe weather|(?:heavy|light) (?:rain|snow)|rain(?:ing|ed)|snow(?:ing|ed))\b", re.I,
)
QUALITATIVE = re.compile(
    r"\b(?:will|won['’]t|expect(?:ed)?|predicted|should (?:be|stay)|no|clear|sunny|cloudy|dry|"
    r"safe|unsafe|low visibility|high risk|severe|possible|likely)\b", re.I,
)
CONDITION_ASSERTION = re.compile(
    r"\b(?:will|won['’]t|expect(?:ed)?|predicted|should (?:be|stay)|no)\b[^.!?]*?"
    r"\b(?:rain(?:fall)?|snow|thunderstorms?|lightning|drizzle|hail|storms?|fog|flood(?:ing)?|clear|sunny|cloudy|dry|"
    r"overcast|freezing|warm|hot|cold)\b", re.I,
)
# Require independently verifiable claims on both sides of assertive conjunctions.
CLAUSES = re.compile(r"(?<=[.!?])\s+|\n+|;|,\s*(?=(?:and|but|while)\b)|\s+(?:and|but|while)\s+", re.I)


# A diagnostic wording marker only. Forecast eligibility still comes from the existing audit.
FORECAST_WORDING = re.compile(r"\b(?:forecast|tomorrow|tonight|overnight|will|expected|predicted)\b", re.I)

# Only simple numeric continuations can inherit the immediately preceding observed location.
# Full matching excludes new places, forecast qualifiers, and incidental factual assertions.
OBSERVED_CONTINUATION = re.compile(
    r"^(?:and\s+)?(?:the\s+)?"
    r"(?:temperature|humidity|wind speed|wind gusts?|it)(?: there)?\s+(?:is|are)\s+"
    r"[−-]?\d+(?:\.\d+)?\s*(?:°\s*C|%|km\s*/\s*h)(?: there)?[.!]?$",
    re.I,
)


def model_weather_answer_is_grounded(text, evidence, auditor, *, weather_request=False):
    """Unknown model weather claims are withheld. Trusted deterministic rendering is audited separately."""
    return first_weather_gate_rejection(text, evidence, auditor, weather_request=weather_request) is None


def first_weather_gate_rejection(text, evidence, auditor, *, weather_request=False):
    """Return bounded structured information about the first rejecting branch."""
    locations = {item.location for item in evidence.items if item.location} if evidence is not None else set()
    source_types = {item.source_type.value for item in evidence.items} if evidence is not None else set()
    observation_only = source_types == {"observed"}
    evidence_scope = {
        frozenset({"observed"}): "observation",
        frozenset({"forecast"}): "forecast",
    }.get(frozenset(source_types), "mixed_or_derived" if source_types else "none")
    anchor = None
    previous_validated = False
    previous_anchor_status = "no_previous_clause"

    def rejected(index, reason, checks=(), numbers=None, audited_numbers=None):
        failed = {
            "missing_evidence": "evidence_required",
            "unsupported_unit": "supported_unit_required",
            "unsafe_certainty": "safe_qualification_required",
            "no_extractable_clause_claim": "extractable_claim_required",
            "clause_claim_audit_failed": "grounded_claims_required",
            "unaudited_number": "all_numbers_must_be_audited",
            "unaudited_condition": "grounded_condition_required",
        }.get(reason)
        if reason == "missing_clause_location":
            if not locations:
                failed = "no_evidence_location"
            elif len(locations) != 1:
                failed = "multiple_evidence_locations"
            elif not observation_only:
                failed = "observation_only_evidence_required"
            elif not anchor:
                failed = "previous_location_anchor_required"
            else:
                failed = "numeric_continuation_required"
        return {
            "clause_index": index, "reason": reason, "claim_checks": list(checks),
            "numeric_mentions": numbers, "audited_numeric_claims": audited_numbers,
            "location_decision": {
                "explicit_evidence_location_detected": bool(mentioned),
                "explicit_location_match_count": len(mentioned),
                "candidate_location_count": len(locations),
                "previous_clause_validated": previous_validated,
                "previous_clause_location_established": bool(anchor),
                "previous_anchor_status": previous_anchor_status,
                "evidence_scope": evidence_scope,
                "forecast_wording_detected": bool(FORECAST_WORDING.search(clause)),
                "numeric_continuation_eligible": numeric_continuation,
                "location_inheritance_attempted": inheritance_attempted,
                "location_inherited": bool(inherited),
                "failed_prerequisite": failed,
            },
        }

    for index, clause in enumerate(CLAUSES.split(text), start=1):
        mentioned = {location for location in locations if re.search(
            r"(?<!\w)" + re.escape(location) + r"(?!\w)", clause, re.I
        )}
        numeric_continuation = bool(OBSERVED_CONTINUATION.fullmatch(clause.strip()))
        inheritance_attempted = inherited = False
        terms = WEATHER_TERMS.search(clause)
        quantities = MEASUREMENT.search(clause)
        numbers = NUMBER.findall(clause)
        prescriptive = re.search(r"\b(?:go ahead|no precautions|safe to|no need for (?:an? )?umbrella)\b", clause, re.I)
        forecast_shape = TIMED_ASSERTION.search(clause) and (numbers or QUALITATIVE.search(clause))
        uncertain = re.search(r"\b(?:could|may|might|if|cannot verify|can’t verify|would need)\b", clause, re.I)
        categorical = CONDITION_FRAGMENT.search(clause) and not uncertain
        assertive = bool(quantities or prescriptive or forecast_shape or categorical
                         or (terms and (numbers or QUALITATIVE.search(clause))))
        if not assertive and not (weather_request and numbers):
            # A standalone weather condition still conveys a factual assertion.
            if not (terms and re.fullmatch(r"[\w -]+[.!]?", clause.strip()) and len(clause.split()) <= 4):
                if clause.strip():
                    anchor = None
                    previous_validated = False
                    previous_anchor_status = "previous_clause_not_audited"
                continue
        if evidence is None:
            return rejected(index, "missing_evidence")
        if UNSUPPORTED_UNIT.search(clause):
            return rejected(index, "unsupported_unit")
        if UNSAFE_CERTAINTY.search(clause):
            return rejected(index, "unsafe_certainty")
        audit_clause = clause
        inheritance_attempted = not mentioned
        inherited = inheritance_attempted and bool(anchor) and numeric_continuation
        if inherited:
            continuation = re.sub(r"\bthere\b\s*", "", clause.strip(), flags=re.I)
            audit_clause = f"Currently in {anchor}, {continuation}"
        elif not mentioned:
            return rejected(index, "missing_clause_location")
        claims, report = auditor.audit(audit_clause, evidence)
        if not report.is_trustworthy:
            checks = ({"variable": row.claim.variable.value, "status": row.status.value}
                      for row in report.validation_results[:8])
            return rejected(index, "clause_claim_audit_failed" if claims else "no_extractable_clause_claim", checks)
        numeric_claims = sum(isinstance(claim.claimed_value, (int, float)) and not isinstance(claim.claimed_value, bool)
                             for claim in claims)
        if len(numbers) > numeric_claims:
            return rejected(index, "unaudited_number", numbers=len(numbers), audited_numbers=numeric_claims)
        if (categorical or CONDITION_ASSERTION.search(clause)) and not any(
            claim.variable.value in {"weather_condition", "precipitation_amount", "precipitation_probability"}
            for claim in claims
        ):
            return rejected(index, "unaudited_condition")
        previous_validated = True
        if observation_only and len(locations) == 1 and len(mentioned) == 1:
            location = next(iter(mentioned))
            prefix = r"^(?:currently\s+)?in\s+" + re.escape(location) + r"(?:,\s*|\s+)"
            metric = re.sub(prefix, "", clause.strip(), count=1, flags=re.I)
            anchor = location if metric != clause.strip() and OBSERVED_CONTINUATION.fullmatch(metric) else None
            previous_anchor_status = "explicit_observation_anchor" if anchor else "anchor_grammar_mismatch"
        elif inherited:
            previous_anchor_status = "inherited_observation_anchor"
        else:
            anchor = None
            previous_anchor_status = "evidence_scope_ineligible"
    return None
