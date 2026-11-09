import re
from typing import Any, Dict, List, Optional

try:
    from backend.evidence.evidence_models import (
        ClaimType,
        FactualClaim,
        WeatherVariable,
    )
except ImportError:
    from evidence.evidence_models import (
        ClaimType,
        FactualClaim,
        WeatherVariable,
    )


class ClaimExtractor:
    """
    Deterministic Factual Claim Extractor for weather responses.
    Parses natural-language AI responses and extracts structured measurable claims
    concerning temperatures, precipitation, wind, humidity, pressure, and trends,
    while filtering out non-factual opinions and general recommendations.
    """

    def __init__(self):
        pass

    def extract_claims(self, text: str, default_location: Optional[str] = None) -> List[FactualClaim]:
        """Extracts all verifiable factual claims from the text."""
        claims: List[FactualClaim] = []
        claim_counter = 1

        if not text or not isinstance(text, str):
            return claims

        # Normalize special unicode characters (e.g. non-breaking spaces, math minus)
        cleaned_text = (
            text.replace("\u202f", " ")
            .replace("\u00a0", " ")
            .replace("\u2212", "-")
            .replace("\u2013", "-")
            .replace("\u2014", "-")
        )

        # Break text into candidate sentences or table rows
        lines = re.split(r"(?<=[.!?\n])\s+", cleaned_text)

        for line in lines:
            line_str = line.strip()
            if not line_str or len(line_str) < 5:
                continue

            # Detect time context for this line/clause
            time_period = self._detect_time_period(line_str)
            location = self._detect_location(line_str, default_location)

            # 1. Temperature Claims
            # Matches patterns like: 23.2 °C, -5°C, 32 degrees, high of 26°C, low of 14°C
            temp_matches = re.finditer(
                r"(?:temperature|temp|feels[\s-]like|apparent\s+temp(?:erature)?|high|low|peak|minimum|maximum)?\s*"
                r"(?:is|at|of|around|near|reaches|reaching|dip(?:s)?\s+to|drops?\s+to)?\s*"
                r"(-?\d+(?:\.\d+)?)\s*(?:°\s*C|degrees?\s*(?:celsius)?|°\s*F)",
                line_str,
                re.IGNORECASE,
            )
            for m in temp_matches:
                val = float(m.group(1))
                prefix = line_str[max(0, m.start() - 25):m.start()].lower()
                local_text = (prefix + " " + m.group(0)).lower()

                var = WeatherVariable.TEMPERATURE
                if "feels" in local_text or "apparent" in local_text:
                    var = WeatherVariable.APPARENT_TEMPERATURE

                claims.append(FactualClaim(
                    claim_id=f"claim_{claim_counter}",
                    statement=line_str,
                    variable=var,
                    claimed_value=val,
                    unit="°C",
                    time_period=time_period,
                    location=location,
                    claim_type=ClaimType.NUMERICAL_VALUE,
                ))
                claim_counter += 1

            # 2. Precipitation Probability Claims
            # Matches: 65% chance of rain, 0% precipitation probability, rain probability of 10%
            prob_matches = re.finditer(
                r"(?:chance\s+of\s+(?:rain|precipitation|showers)|precip(?:itation)?\s+(?:probability|chance)|rain\s+probability)\s*"
                r"(?:is|of|at|around|reach(?:es)?|peak(?:s)?\s+(?:at)?|remains?)?\s*"
                r"(\d+(?:\.\d+)?)\s*%",
                line_str,
                re.IGNORECASE,
            )
            for m in prob_matches:
                val = float(m.group(1))
                claims.append(FactualClaim(
                    claim_id=f"claim_{claim_counter}",
                    statement=line_str,
                    variable=WeatherVariable.PRECIPITATION_PROBABILITY,
                    claimed_value=val,
                    unit="%",
                    time_period=time_period,
                    location=location,
                    claim_type=ClaimType.NUMERICAL_VALUE,
                ))
                claim_counter += 1

            # Matches reverse syntax: "0 % chance of rain", "80% probability of precipitation"
            rev_prob_matches = re.finditer(
                r"(\d+(?:\.\d+)?)\s*%\s*(?:chance|probability)\s+(?:of\s+)?(?:rain|precipitation|showers)",
                line_str,
                re.IGNORECASE,
            )
            for m in rev_prob_matches:
                val = float(m.group(1))
                # avoid duplicate if already matched by prob_matches on same line with same value
                if not any(c.variable == WeatherVariable.PRECIPITATION_PROBABILITY and c.claimed_value == val for c in claims[-2:]):
                    claims.append(FactualClaim(
                        claim_id=f"claim_{claim_counter}",
                        statement=line_str,
                        variable=WeatherVariable.PRECIPITATION_PROBABILITY,
                        claimed_value=val,
                        unit="%",
                        time_period=time_period,
                        location=location,
                        claim_type=ClaimType.NUMERICAL_VALUE,
                    ))
                    claim_counter += 1

            # 3. Precipitation Amount / Accumulation Claims
            # Matches: 0.0 mm of rain, 2.5 mm expected rainfall, 10 mm precipitation
            rain_amt_matches = re.finditer(
                r"(\d+(?:\.\d+)?)\s*mm\s*(?:of\s+)?(?:rain|precipitation|rainfall|rain\s+expected|accumulated)?",
                line_str,
                re.IGNORECASE,
            )
            for m in rain_amt_matches:
                val = float(m.group(1))
                claims.append(FactualClaim(
                    claim_id=f"claim_{claim_counter}",
                    statement=line_str,
                    variable=WeatherVariable.PRECIPITATION_AMOUNT,
                    claimed_value=val,
                    unit="mm",
                    time_period=time_period,
                    location=location,
                    claim_type=ClaimType.NUMERICAL_VALUE,
                ))
                claim_counter += 1

            # 4. Humidity Claims
            # Matches: humidity is 67%, relative humidity 75%, humidity around 50%
            hum_matches = re.finditer(
                r"(?:relative\s+)?humidity\s*(?:is|at|of|around|near|reach(?:es)?|remains?)?\s*(\d+(?:\.\d+)?)\s*%",
                line_str,
                re.IGNORECASE,
            )
            for m in hum_matches:
                val = float(m.group(1))
                claims.append(FactualClaim(
                    claim_id=f"claim_{claim_counter}",
                    statement=line_str,
                    variable=WeatherVariable.HUMIDITY,
                    claimed_value=val,
                    unit="%",
                    time_period=time_period,
                    location=location,
                    claim_type=ClaimType.NUMERICAL_VALUE,
                ))
                claim_counter += 1

            # 5. Wind Speed Claims
            # Matches: wind speed of 12 km/h, winds at 25 km/h, 0.2 km/h from north
            wind_matches = re.finditer(
                r"(?:wind\s*(?:speed)?|winds?|breeze)?\s*"
                r"(?:is|at|of|around|near|reaches|reaching)?\s*"
                r"(\d+(?:\.\d+)?)\s*(?:km\s*/\s*h|km\s*h[-⁻]1|kmh|mph|m\s*/\s*s)",
                line_str,
                re.IGNORECASE,
            )
            for m in wind_matches:
                val = float(m.group(1))
                # Skip if matching temperature or other non-wind number
                if "km" in m.group(0).lower():
                    claims.append(FactualClaim(
                        claim_id=f"claim_{claim_counter}",
                        statement=line_str,
                        variable=WeatherVariable.WIND_SPEED,
                        claimed_value=val,
                        unit="km/h",
                        time_period=time_period,
                        location=location,
                        claim_type=ClaimType.NUMERICAL_VALUE,
                    ))
                    claim_counter += 1

            # 6. Pressure Claims
            # Matches: pressure of 943.8 hPa, 1013 hPa
            press_matches = re.finditer(
                r"(?:surface\s+)?pressure\s*(?:is|of|at|around)?\s*(\d+(?:\.\d+)?)\s*hPa",
                line_str,
                re.IGNORECASE,
            )
            for m in press_matches:
                val = float(m.group(1))
                claims.append(FactualClaim(
                    claim_id=f"claim_{claim_counter}",
                    statement=line_str,
                    variable=WeatherVariable.PRESSURE,
                    claimed_value=val,
                    unit="hPa",
                    time_period=time_period,
                    location=location,
                    claim_type=ClaimType.NUMERICAL_VALUE,
                ))
                claim_counter += 1

            # 7. Cloud Cover Claims
            cloud_matches = re.finditer(
                r"cloud\s+cover\s*(?:is|of|at|around)?\s*(\d+(?:\.\d+)?)\s*%",
                line_str,
                re.IGNORECASE,
            )
            for m in cloud_matches:
                val = float(m.group(1))
                claims.append(FactualClaim(
                    claim_id=f"claim_{claim_counter}",
                    statement=line_str,
                    variable=WeatherVariable.CLOUD_COVER,
                    claimed_value=val,
                    unit="%",
                    time_period=time_period,
                    location=location,
                    claim_type=ClaimType.NUMERICAL_VALUE,
                ))
                claim_counter += 1

            # 8. Qualitative / Trend Claims
            line_lower = line_str.lower()
            if any(k in line_lower for k in [
                "temperature is increasing", "temperatures are increasing",
                "temperatures are rising", "temperature is rising",
                "temperatures increase", "temperature increases",
                "upward trend"
            ]):
                claims.append(FactualClaim(
                    claim_id=f"claim_{claim_counter}",
                    statement=line_str,
                    variable=WeatherVariable.TEMPERATURE_TREND,
                    claimed_value="increasing",
                    unit="trend",
                    time_period=time_period,
                    location=location,
                    claim_type=ClaimType.TREND,
                ))
                claim_counter += 1
            elif any(k in line_lower for k in [
                "temperature is decreasing", "temperatures are decreasing",
                "temperatures are dropping", "temperature is dropping",
                "temperatures will fall", "temperature falls",
                "downward trend"
            ]):
                claims.append(FactualClaim(
                    claim_id=f"claim_{claim_counter}",
                    statement=line_str,
                    variable=WeatherVariable.TEMPERATURE_TREND,
                    claimed_value="decreasing",
                    unit="trend",
                    time_period=time_period,
                    location=location,
                    claim_type=ClaimType.TREND,
                ))
                claim_counter += 1
            elif any(k in line_lower for k in ["temperature remains steady", "temperatures stay steady", "temperatures remain constant", "essentially unchanged"]):
                claims.append(FactualClaim(
                    claim_id=f"claim_{claim_counter}",
                    statement=line_str,
                    variable=WeatherVariable.TEMPERATURE_TREND,
                    claimed_value="steady",
                    unit="trend",
                    time_period=time_period,
                    location=location,
                    claim_type=ClaimType.TREND,
                ))
                claim_counter += 1

            # 9. Umbrella Need Claim
            if any(k in line_lower for k in ["no umbrella needed", "leave the umbrella at home", "umbrella is unnecessary", "don't need an umbrella", "do not need an umbrella"]):
                claims.append(FactualClaim(
                    claim_id=f"claim_{claim_counter}",
                    statement=line_str,
                    variable=WeatherVariable.UMBRELLA_NEED,
                    claimed_value=False,
                    unit="recommendation",
                    time_period=time_period,
                    location=location,
                    claim_type=ClaimType.RECOMMENDATION_SUPPORT,
                ))
                claim_counter += 1
            elif any(k in line_lower for k in ["carry an umbrella", "take an umbrella", "umbrella is recommended", "umbrella is advised"]):
                claims.append(FactualClaim(
                    claim_id=f"claim_{claim_counter}",
                    statement=line_str,
                    variable=WeatherVariable.UMBRELLA_NEED,
                    claimed_value=True,
                    unit="recommendation",
                    time_period=time_period,
                    location=location,
                    claim_type=ClaimType.RECOMMENDATION_SUPPORT,
                ))
                claim_counter += 1

        return claims

    def _detect_time_period(self, text: str) -> str:
        """Heuristically extracts time references from a statement."""
        text_lower = text.lower()

        # Specific ISO timestamp e.g. 2026-11-09T16:00
        iso_match = re.search(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\b", text)
        if iso_match:
            return iso_match.group(0)

        # Hour references e.g. 16:00, 5 PM
        hour_match = re.search(r"\b(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm)?|\d{2}:\d{2})\b", text, re.IGNORECASE)

        if "tomorrow" in text_lower:
            return "tomorrow"
        if "today" in text_lower:
            return "today"
        if "right now" in text_lower or "currently" in text_lower or "as of" in text_lower:
            return "current"
        if "morning" in text_lower:
            return "morning"
        if "afternoon" in text_lower:
            return "afternoon"
        if "evening" in text_lower:
            return "evening"
        if "night" in text_lower:
            return "night"

        if hour_match:
            return hour_match.group(0).strip()

        return "forecast_period"

    def _detect_location(self, text: str, default_location: Optional[str]) -> Optional[str]:
        """Detects mentioned location or falls back to default."""
        if default_location and default_location.lower() in text.lower():
            return default_location
        return default_location
