"""Allowlisted metrics. Provider bodies, tool payloads and response prose stay in memory."""
import re


def assess(case, result, state):
    text = result.get("response", "")
    report = result.get("validation_report") or {}
    validations = report.get("validation_results", [])
    numeric = re.search(r"\d\s*(?:°\s*[CF]|%|km\s*/\s*h|mm\b)", text, re.I)
    unsupported = sum(
        type(row["claim"].get("claimed_value")) in (int, float) and row.get("status") != "SUPPORTED"
        for row in validations
    )
    unaudited = bool(numeric and not any(
        type(row["claim"].get("claimed_value")) in (int, float) for row in validations
    ))
    covered = {place: set() for place in case.places}
    for row in validations:
        claim = row["claim"]
        if row.get("status") != "SUPPORTED" or not row.get("supporting_evidence_ids"):
            continue
        for place in covered:
            if re.search(r"(?<!\w)" + re.escape(place) + r"(?!\w)", claim["statement"], re.I):
                covered[place].add(claim["variable"])
    hazards = [
        item["condition"] for item in (result.get("risk_assessment") or {}).get("detected_risks", [])
        if item["severity"] in {"HIGH", "SEVERE"}
    ]
    hazard_ok = all(hazard.casefold() in text.casefold() for hazard in hazards)
    scope = case.period in text.casefold()
    if case.period == "current":
        scope = bool(re.search(r"\b(?:observed|current|right now)\b", text, re.I))
    anchor = getattr(state, "last_confirmed_location", None)
    follow_up_ok = not case.follow_up or bool(anchor and anchor.name.casefold() == case.places[0].casefold())
    measurements_ok = all(set(case.measurements) <= values for values in covered.values())
    if case.name == "umbrella":
        measurements_ok &= bool(re.search(r"umbrella|rain protection", text, re.I))
    limitation = bool(re.search(r"unavailable|can’t verify|don’t have|couldn’t verify", text, re.I))
    passed = ((limitation and not numeric) if case.unsupported else
              bool(report.get("is_trustworthy") and measurements_ok and scope and follow_up_ok and hazard_ok))
    return {
        "pass": passed and not unsupported and not unaudited,
        "evidence_trustworthy": report.get("is_trustworthy"),
        "agent_answer_complete": (result.get("token_usage") or {}).get("answer_complete"),
        "measurement_coverage": {place: sorted(fields) for place, fields in covered.items()},
        "period_mentioned": scope, "follow_up_anchor_ok": follow_up_ok,
        "material_hazards_detected": len(hazards), "material_hazards_covered": hazard_ok if hazards else None,
        "unsupported_numeric_claims": unsupported, "unaudited_numeric_answer": unaudited,
    }
