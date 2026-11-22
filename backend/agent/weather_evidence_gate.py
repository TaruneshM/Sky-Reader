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


def model_weather_answer_is_grounded(text, evidence, auditor, *, weather_request=False):
    """Unknown model weather claims are withheld. Trusted deterministic rendering is audited separately."""
    for clause in CLAUSES.split(text):
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
                continue
        if evidence is None or UNSUPPORTED_UNIT.search(clause) or UNSAFE_CERTAINTY.search(clause):
            return False
        if not any(item.location and re.search(
            r"(?<!\w)" + re.escape(item.location) + r"(?!\w)", clause, re.I
        ) for item in evidence.items):
            return False
        claims, report = auditor.audit(clause, evidence)
        if not report.is_trustworthy:
            return False
        numeric_claims = sum(isinstance(claim.claimed_value, (int, float)) and not isinstance(claim.claimed_value, bool)
                             for claim in claims)
        if len(numbers) > numeric_claims:
            return False
        if (categorical or CONDITION_ASSERTION.search(clause)) and not any(
            claim.variable.value in {"weather_condition", "precipitation_amount", "precipitation_probability"}
            for claim in claims
        ):
            return False
    return True
