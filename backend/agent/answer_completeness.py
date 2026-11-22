"""Check whether an audited answer covers the weather question."""
from dataclasses import dataclass
import re


COMPLEX_REQUEST = re.compile(
    r"\b(?:comprehensive(?:ly)?|in detail|detailed|breakdown|deep dive|meteorological|"
    r"why|explain|trade[- ]offs?|hour by hour|multi.day|trends?)\b", re.I,
)

ADVICE_INTENTS = {"coat_clothing", "morning_walk", "umbrella", "weather_risks"}
METRIC_CLAIMS = {
    "temperature": "temperature",
    "conditions": "weather_condition",
    "rain probability": "precipitation_probability",
    "rainfall": "precipitation_amount",
    "wind speed": "wind_speed",
    "wind gusts": "wind_gust",
    "humidity": "humidity",
    "risk": "travel_suitability",
}


@dataclass(frozen=True)
class AnswerRequirements:
    measurements: tuple[tuple[str, ...], ...]
    hazards: tuple[str, ...] = ()
    advice: str | None = None

    def missing_data(self, available):
        return tuple(" or ".join(group) for group in self.measurements if not set(group) & available)

    def omissions(self, text, report, evidence, *, location, period=None):
        """Use supported claim provenance for metric coverage, and require material guidance."""
        covered = set()
        for row in report.validation_results:
            if row.status.value != "SUPPORTED":
                continue
            for evidence_id in row.supporting_evidence_ids:
                item = evidence.get_by_id(evidence_id)
                if item and item.location == location and (
                    period is None or item.metadata.get("requested_period") == period
                ):
                    covered.update(key for key, variable in METRIC_CLAIMS.items() if variable == row.claim.variable.value)
        missing = list(self.missing_data(covered))
        normalized = text.casefold()
        missing.extend(hazard for hazard in self.hazards if hazard.casefold() not in normalized)
        if self.advice and self.advice.casefold() not in normalized:
            missing.append("recommendation")
        return tuple(missing)


def requirements(intent, message, *, forecast, risk=None, advice=None, components=()):
    rain = ("rain probability", "rainfall")
    weather = (("temperature",), rain, ("wind speed",))
    scopes = {
        "temperature": (("temperature",),),
        "rain_check": (rain,),
        "umbrella": (rain, ("risk",)),
        "tomorrow_forecast": weather,
        "coat_clothing": (*weather, ("risk",)),
        "morning_walk": (*weather, ("risk",)),
        "weather_risks": (("risk",),),
        "comparison": (*weather, ("risk",)),
        "current_weather": weather if forecast else (("temperature",), ("conditions",)),
    }
    if intent == "wind_humidity":
        groups = []
        if re.search(r"\bhumid(?:ity)?\b", message, re.I):
            groups.append(("humidity",))
        if re.search(r"\bwind(?:y|s)?\b", message, re.I) or not groups:
            groups.append(("wind gusts",) if re.search(r"\bgusts?\b", message, re.I) else ("wind speed",))
        scopes[intent] = tuple(groups)
    selected = list(scopes.get(intent, (("temperature",),)))
    component_groups = {
        "temperature": (("temperature",),),
        "rain": (rain,),
        "wind speed": (("wind speed",),),
        "wind gusts": (("wind gusts",),),
        "humidity": (("humidity",),),
        "forecast": weather if forecast else (("temperature",), ("conditions",)),
        "clothing": (*weather, ("risk",)),
        "umbrella": (rain, ("risk",)),
        "safety": (("risk",),),
    }
    for component in components:
        for group in component_groups.get(component, ()):
            if group not in selected:
                selected.append(group)
    hazards = tuple(item["condition"] for item in (risk or {}).get("detected_risks", ())
                    if item["severity"] in {"HIGH", "SEVERE"})
    return AnswerRequirements(tuple(selected), hazards, advice)

