import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

try:
    from backend.evaluation.models import TestCase, WeatherFixture
    from backend.evaluation.result_models import EvaluationResult, ExecutionStatus
    from backend.evaluation.metrics.base import (
        BaseMetricEvaluator,
        BaseMetricResult,
        MetricStatus,
        NumericalMatchStatus,
    )
except ImportError:
    from evaluation.models import TestCase, WeatherFixture
    from evaluation.result_models import EvaluationResult, ExecutionStatus
    from evaluation.metrics.base import (
        BaseMetricEvaluator,
        BaseMetricResult,
        MetricStatus,
        NumericalMatchStatus,
    )


class VariableNumericalResult(BaseModel):
    """
    Detailed numerical evaluation result for a single expected weather variable.
    """
    variable_name: str
    expected_value: float
    tolerance: float
    extracted_value: Optional[float] = None
    extracted_raw_unit: Optional[str] = None
    converted_value: Optional[float] = None
    status: NumericalMatchStatus = NumericalMatchStatus.MISSING
    absolute_error: Optional[float] = None
    notes: Optional[str] = None


class NumericalMetricResult(BaseMetricResult):
    """
    Evaluation output for numerical accuracy across all expected measurements.
    """
    total_expected: int = 0
    correct_count: int = 0
    incorrect_count: int = 0
    missing_count: int = 0
    accuracy: Optional[float] = None
    mean_absolute_error: Optional[float] = None
    variable_results: Dict[str, VariableNumericalResult] = Field(default_factory=dict)


class NumericalAccuracyEvaluator(BaseMetricEvaluator):
    """
    Deterministically extracts and compares meteorological measurements from system responses
    against ground-truth expected numerical values with unit normalization and tolerance margins.
    """

    def __init__(self):
        pass

    def evaluate(
        self,
        result: EvaluationResult,
        test_case: TestCase,
        fixture: Optional[WeatherFixture] = None,
    ) -> NumericalMetricResult:
        # Check execution health first
        if result.execution_status != ExecutionStatus.COMPLETED:
            return NumericalMetricResult(
                is_evaluable=False,
                reason_unevaluable=f"Execution did not complete (status={result.execution_status.value}, error={result.error_type}: {result.error_message})",
                metric_status=MetricStatus.UNEVALUABLE,
                total_expected=len(test_case.expected_numerical_values),
            )

        expected_values = test_case.expected_numerical_values
        if not expected_values:
            return NumericalMetricResult(
                is_evaluable=True,
                metric_status=MetricStatus.NOT_APPLICABLE,
                total_expected=0,
                accuracy=None,
            )

        tolerances = test_case.evaluation_criteria.allowed_numerical_tolerances
        response_text = result.response or ""

        # Extract candidates from response text and claims
        extracted_by_var = self._extract_meteorological_values(response_text, result.claims)

        var_results: Dict[str, VariableNumericalResult] = {}
        correct_count = 0
        incorrect_count = 0
        missing_count = 0
        errors: List[float] = []

        for var_name, expected_val in expected_values.items():
            tol = tolerances.get(var_name, 0.5)

            # Retrieve candidates extracted for this variable family
            candidates = self._find_matching_candidates(var_name, extracted_by_var, expected_val)

            if not candidates:
                var_results[var_name] = VariableNumericalResult(
                    variable_name=var_name,
                    expected_value=float(expected_val),
                    tolerance=float(tol),
                    status=NumericalMatchStatus.MISSING,
                    notes="No matching numerical measurement found in response.",
                )
                missing_count += 1
                continue

            # Pick candidate with minimum error
            best_candidate = min(candidates, key=lambda c: abs(c["converted_value"] - expected_val))
            extracted_val = best_candidate["raw_value"]
            converted_val = best_candidate["converted_value"]
            unit_found = best_candidate.get("unit")
            abs_err = round(abs(converted_val - expected_val), 4)

            if abs_err <= tol:
                status = NumericalMatchStatus.CORRECT
                correct_count += 1
            else:
                status = NumericalMatchStatus.INCORRECT
                incorrect_count += 1

            errors.append(abs_err)
            var_results[var_name] = VariableNumericalResult(
                variable_name=var_name,
                expected_value=float(expected_val),
                tolerance=float(tol),
                extracted_value=float(extracted_val),
                extracted_raw_unit=unit_found,
                converted_value=float(converted_val),
                status=status,
                absolute_error=float(abs_err),
                notes=best_candidate.get("context"),
            )

        total_expected = len(expected_values)
        accuracy = round(correct_count / total_expected, 4) if total_expected > 0 else None
        mae = round(sum(errors) / len(errors), 4) if errors else None

        if correct_count == total_expected:
            overall_status = MetricStatus.PASSED
        elif correct_count > 0:
            overall_status = MetricStatus.PARTIAL
        else:
            overall_status = MetricStatus.FAILED

        return NumericalMetricResult(
            is_evaluable=True,
            metric_status=overall_status,
            total_expected=total_expected,
            correct_count=correct_count,
            incorrect_count=incorrect_count,
            missing_count=missing_count,
            accuracy=accuracy,
            mean_absolute_error=mae,
            variable_results=var_results,
        )

    def _convert_unit(self, val: float, unit: str, target_family: str) -> Tuple[float, str]:
        """
        Converts non-standard units to canonical SI / benchmark units:
        - Temperature -> °C
        - Wind speed -> km/h
        - Precipitation -> mm
        - Pressure -> hPa
        """
        unit_clean = unit.strip().lower()

        # Temperature: Fahrenheit -> Celsius
        if target_family in ("temperature", "apparent_temperature", "temp", "temp_max", "temp_min", "dew_point"):
            if "f" in unit_clean and "c" not in unit_clean:
                # Fahrenheit to Celsius
                celsius = (val - 32.0) * (5.0 / 9.0)
                return (round(celsius, 2), "°C")
            return (val, "°C")

        # Wind speed: mph, m/s, knots -> km/h
        if target_family in ("wind_speed", "wind_gusts", "max_wind_speed", "wind"):
            if "mph" in unit_clean:
                return (round(val * 1.60934, 2), "km/h")
            if "m/s" in unit_clean or "mps" in unit_clean:
                return (round(val * 3.6, 2), "km/h")
            if "knot" in unit_clean or "kt" in unit_clean:
                return (round(val * 1.852, 2), "km/h")
            return (val, "km/h")

        # Precipitation: inches, cm -> mm
        if target_family in ("precipitation_amount", "rainfall", "total_rain", "rain", "total_expected_rain_mm"):
            if "in" in unit_clean or "inch" in unit_clean:
                return (round(val * 25.4, 2), "mm")
            if "cm" in unit_clean:
                return (round(val * 10.0, 2), "mm")
            return (val, "mm")

        # Pressure: inHg -> hPa
        if target_family in ("pressure", "surface_pressure"):
            if "inhg" in unit_clean:
                return (round(val * 33.8639, 2), "hPa")
            return (val, "hPa")

        return (val, unit)

    def _extract_meteorological_values(
        self,
        text: str,
        claims: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scans text using deterministic regex patterns to extract candidates grouped by variable category.
        Also parses structured claims if present.
        """
        extracted: Dict[str, List[Dict[str, Any]]] = {
            "temperature": [],
            "humidity": [],
            "precipitation_probability": [],
            "precipitation_amount": [],
            "wind_speed": [],
            "pressure": [],
            "cloud_cover": [],
            "general_number": [],
        }

        # 1. Incorporate structured claims from Phase 4 if present
        if claims:
            for c in claims:
                val = c.get("claimed_value")
                if isinstance(val, (int, float)):
                    var = str(c.get("variable", "")).lower()
                    unit = c.get("unit") or ""
                    # Map to category
                    for cat in extracted:
                        if cat in var or var in cat:
                            converted, canon_unit = self._convert_unit(float(val), unit, cat)
                            extracted[cat].append({
                                "raw_value": float(val),
                                "converted_value": converted,
                                "unit": unit or canon_unit,
                                "context": f"Claim: {c.get('statement', '')}",
                            })

        # 2. Extract from response text using targeted regex

        # --- A. Temperature Patterns ---
        # e.g. "21.8°C", "21.8 °C", "-5°C", "71.2°F", "21.8 degrees Celsius"
        temp_pattern = re.compile(
            r"(?<!\d:)(?<!\d)([-+]?\d+(?:\.\d+)?)\s*(?:°\s*([CcFf])|deg(?:rees)?\s*([CcFf]|celsius|fahrenheit)|celsius|fahrenheit)\b",
            re.IGNORECASE,
        )
        for match in temp_pattern.finditer(text):
            val_str = match.group(1)
            unit_str = match.group(2) or match.group(3) or "C"
            val = float(val_str)
            # Skip unrealistic meteorological values (> 70°C or < -90°C unless Fahrenheit)
            if "f" not in unit_str.lower() and (val > 65.0 or val < -85.0):
                continue
            converted, canon = self._convert_unit(val, unit_str, "temperature")
            extracted["temperature"].append({
                "raw_value": val,
                "converted_value": converted,
                "unit": unit_str,
                "context": match.group(0),
            })

        # Words like "temperature of 21.8", "temp is 21.8", "around 21.8"
        temp_context_pattern = re.compile(
            r"(?:temperature|temp|high|low|apparent temperature|feels like)\s*(?:of|is|around|about|approximately|reached|dropping to|reach(?:es)?)?\s*([-+]?\d+(?:\.\d+)?)\s*(?:°|deg)?(?:\s*([CcFf]))?\b",
            re.IGNORECASE,
        )
        for match in temp_context_pattern.finditer(text):
            val_str = match.group(1)
            unit_str = match.group(2) or "C"
            val = float(val_str)
            if -80.0 <= val <= 135.0:
                converted, canon = self._convert_unit(val, unit_str, "temperature")
                extracted["temperature"].append({
                    "raw_value": val,
                    "converted_value": converted,
                    "unit": unit_str,
                    "context": match.group(0),
                })

        # --- B. Humidity Patterns ---
        # e.g. "88% humidity", "humidity: 88%", "humidity of 88%"
        humidity_pattern = re.compile(
            r"(?:humidity|relative humidity)\s*(?:of|is|around|about|at|:)?\s*(\d+(?:\.\d+)?)\s*%",
            re.IGNORECASE,
        )
        for match in humidity_pattern.finditer(text):
            val = float(match.group(1))
            if 0.0 <= val <= 100.0:
                extracted["humidity"].append({
                    "raw_value": val,
                    "converted_value": val,
                    "unit": "%",
                    "context": match.group(0),
                })
        humidity_post_pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*%\s*(?:relative )?humidity\b",
            re.IGNORECASE,
        )
        for match in humidity_post_pattern.finditer(text):
            val = float(match.group(1))
            if 0.0 <= val <= 100.0:
                extracted["humidity"].append({
                    "raw_value": val,
                    "converted_value": val,
                    "unit": "%",
                    "context": match.group(0),
                })

        # --- C. Precipitation Probability Patterns ---
        # e.g. "60% chance of rain", "precipitation probability is 80%"
        pop_pattern = re.compile(
            r"(?:precipitation|rain|chance of rain|precip probability|probability of precipitation)\s*(?:probability|chance)?\s*(?:of|is|around|about|at|:)?\s*(\d+(?:\.\d+)?)\s*%",
            re.IGNORECASE,
        )
        for match in pop_pattern.finditer(text):
            val = float(match.group(1))
            if 0.0 <= val <= 100.0:
                extracted["precipitation_probability"].append({
                    "raw_value": val,
                    "converted_value": val,
                    "unit": "%",
                    "context": match.group(0),
                })
        pop_post_pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*%\s*(?:chance of (?:rain|precipitation)|precipitation probability|probability of rain)",
            re.IGNORECASE,
        )
        for match in pop_post_pattern.finditer(text):
            val = float(match.group(1))
            if 0.0 <= val <= 100.0:
                extracted["precipitation_probability"].append({
                    "raw_value": val,
                    "converted_value": val,
                    "unit": "%",
                    "context": match.group(0),
                })

        # --- D. Precipitation Amount Patterns ---
        # e.g. "18.5 mm", "18.5mm of rain", "0.73 inches of precipitation"
        rain_pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*(mm|millimeters?|cm|inches?|in)\s*(?:of\s+(?:rain|rainfall|precipitation|accumulation))?",
            re.IGNORECASE,
        )
        for match in rain_pattern.finditer(text):
            val = float(match.group(1))
            unit = match.group(2)
            # Avoid mistaking "in" as preposition (e.g. "10 in London")
            if unit.lower() == "in" and "rain" not in match.group(0).lower() and "precipitation" not in match.group(0).lower():
                continue
            converted, canon = self._convert_unit(val, unit, "precipitation_amount")
            extracted["precipitation_amount"].append({
                "raw_value": val,
                "converted_value": converted,
                "unit": unit,
                "context": match.group(0),
            })

        # --- E. Wind Speed Patterns ---
        # e.g. "15.2 km/h", "68.0 km/h wind", "10 mph", "12 m/s"
        wind_pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*(km\/h|kmh|km\/hr|kph|m\/s|mph|knots?)\b",
            re.IGNORECASE,
        )
        for match in wind_pattern.finditer(text):
            val = float(match.group(1))
            unit = match.group(2)
            converted, canon = self._convert_unit(val, unit, "wind_speed")
            extracted["wind_speed"].append({
                "raw_value": val,
                "converted_value": converted,
                "unit": unit,
                "context": match.group(0),
            })

        # --- F. Surface Pressure Patterns ---
        # e.g. "1013.2 hPa", "1015 mb"
        pressure_pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*(hPa|mb|millibars?|inHg)\b",
            re.IGNORECASE,
        )
        for match in pressure_pattern.finditer(text):
            val = float(match.group(1))
            unit = match.group(2)
            converted, canon = self._convert_unit(val, unit, "pressure")
            extracted["pressure"].append({
                "raw_value": val,
                "converted_value": converted,
                "unit": unit,
                "context": match.group(0),
            })

        # --- G. General Numbers Fallback ---
        # Extracts isolated numbers while avoiding timestamps (14:00), years (2026), or ordinals (1st)
        general_pattern = re.compile(
            r"(?<![\d:])(?<![-+])\b([-+]?\d+(?:\.\d+)?)\b(?!:)(?!st\b)(?!nd\b)(?!rd\b)(?!th\b)",
        )
        for match in general_pattern.finditer(text):
            val = float(match.group(1))
            # Ignore standard calendar years and timestamps
            if val in (2023, 2024, 2025, 2026, 2027, 2030, 2036):
                continue
            extracted["general_number"].append({
                "raw_value": val,
                "converted_value": val,
                "unit": None,
                "context": match.group(0),
            })

        return extracted

    def _find_matching_candidates(
        self,
        target_name: str,
        extracted_by_var: Dict[str, List[Dict[str, Any]]],
        expected_val: float,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves candidate extracted values that match the target variable category.
        """
        target_lower = target_name.lower()
        candidates: List[Dict[str, Any]] = []

        if "temp" in target_lower or "warming" in target_lower or "freeze" in target_lower or "drop" in target_lower:
            candidates.extend(extracted_by_var["temperature"])
        elif "humid" in target_lower:
            candidates.extend(extracted_by_var["humidity"])
        elif "precip" in target_lower and ("prob" in target_lower or "chance" in target_lower or "%" in target_lower):
            candidates.extend(extracted_by_var["precipitation_probability"])
        elif "rain" in target_lower or "precip" in target_lower or "monsoon" in target_lower or "accumulation" in target_lower:
            candidates.extend(extracted_by_var["precipitation_amount"])
        elif "wind" in target_lower or "gust" in target_lower:
            candidates.extend(extracted_by_var["wind_speed"])
        elif "press" in target_lower:
            candidates.extend(extracted_by_var["pressure"])
        elif "cloud" in target_lower:
            candidates.extend(extracted_by_var["cloud_cover"])
        else:
            # Only use general numbers for generic, unclassified target variables
            candidates.extend(extracted_by_var["general_number"])

        return candidates
