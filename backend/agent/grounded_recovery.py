"""Render a limited delivery recovery from trusted observation evidence."""
from math import isfinite

from .answer_completeness import requirements
from .weather_evidence_gate import model_weather_answer_is_grounded


def recover_observed_temperature(task, destination, evidence, auditor, question):
    if (destination is None or destination.requirement != "current" or destination.period != "current"
            or destination.status != "available" or evidence is None or task.intent != "temperature"
            or task.comparison or task.safety or task.activity or task.relative_baseline):
        return None
    contract = requirements(task.intent, question, forecast=False, components=task.components)
    if contract.measurements != (("temperature",),) or contract.hazards or contract.advice:
        return None
    place = destination.place
    items = evidence.items
    if not items or any(item.location != place.name or item.source_type.value != "observed"
                        or item.latitude != place.latitude or item.longitude != place.longitude for item in items):
        return None
    temperatures = [item for item in items if item.variable.value == "temperature"]
    if len(temperatures) != 1:
        return None
    item = temperatures[0]
    if item.unit != "°C" or type(item.value) not in (int, float) or not isfinite(item.value):
        return None
    # Use the observed period, never a guessed timestamp or anything from the rejected draft.
    number = str(item.value)
    if number.endswith(".0"):
        number = number[:-2]
    text = (f"Currently in {place.name}, the observed temperature is {number} °C. "
            "I couldn’t verify a detailed explanation.")
    if not model_weather_answer_is_grounded(text, evidence, auditor, weather_request=True):
        return None
    claims, report = auditor.audit(text, evidence)
    if not report.is_trustworthy or contract.omissions(text, report, evidence, location=place.name):
        return None
    if not any(item.id in row.supporting_evidence_ids for row in report.validation_results):
        return None
    return text, (claims, report)
