import sys
from pathlib import Path

# Ensure backend directory is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.evidence.evidence_models import (
    ClaimType,
    WeatherVariable,
)
from backend.evidence.claim_extractor import ClaimExtractor


def test_claim_extractor():
    print("Testing ClaimExtractor...")
    extractor = ClaimExtractor()

    # 1. Test Temperature and Apparent Temperature
    sample_text = (
        "The current temperature in Dehradun is 22.5 °C. "
        "The feels-like apparent temperature is 24.0 °C."
    )
    claims = extractor.extract_claims(sample_text, default_location="Dehradun")
    assert len(claims) == 2
    temp_claims = [c for c in claims if c.variable == WeatherVariable.TEMPERATURE]
    feels_claims = [c for c in claims if c.variable == WeatherVariable.APPARENT_TEMPERATURE]

    assert len(temp_claims) == 1
    assert temp_claims[0].claimed_value == 22.5
    assert temp_claims[0].unit == "°C"
    assert temp_claims[0].location == "Dehradun"

    assert len(feels_claims) == 1
    assert feels_claims[0].claimed_value == 24.0
    assert feels_claims[0].unit == "°C"

    # 2. Test Precipitation Probability & Amount
    precip_text = (
        "There is a 65% chance of rain in the afternoon. "
        "Total precipitation is expected to be 2.5 mm."
    )
    claims_p = extractor.extract_claims(precip_text, default_location="Dehradun")
    prob_claims = [c for c in claims_p if c.variable == WeatherVariable.PRECIPITATION_PROBABILITY]
    amt_claims = [c for c in claims_p if c.variable == WeatherVariable.PRECIPITATION_AMOUNT]

    assert len(prob_claims) == 1
    assert prob_claims[0].claimed_value == 65.0
    assert prob_claims[0].unit == "%"
    assert prob_claims[0].time_period == "afternoon"

    assert len(amt_claims) == 1
    assert amt_claims[0].claimed_value == 2.5
    assert amt_claims[0].unit == "mm"

    # 3. Test Humidity and Wind Speed
    hw_text = (
        "Relative humidity is 65% and wind speed is 12 km/h."
    )
    claims_hw = extractor.extract_claims(hw_text)
    hum_claims = [c for c in claims_hw if c.variable == WeatherVariable.HUMIDITY]
    wind_claims = [c for c in claims_hw if c.variable == WeatherVariable.WIND_SPEED]

    assert len(hum_claims) == 1
    assert hum_claims[0].claimed_value == 65.0
    assert len(wind_claims) == 1
    assert wind_claims[0].claimed_value == 12.0
    assert wind_claims[0].unit == "km/h"

    # 4. Test Trend Claims
    trend_text = "The temperature is increasing over the next few hours."
    claims_tr = extractor.extract_claims(trend_text)
    assert len(claims_tr) == 1
    assert claims_tr[0].variable == WeatherVariable.TEMPERATURE_TREND
    assert claims_tr[0].claimed_value == "increasing"
    assert claims_tr[0].claim_type == ClaimType.TREND

    # 5. Test Umbrella Recommendation Support
    umb_text_1 = "You do not need an umbrella today."
    claims_u1 = extractor.extract_claims(umb_text_1)
    assert len(claims_u1) == 1
    assert claims_u1[0].variable == WeatherVariable.UMBRELLA_NEED
    assert claims_u1[0].claimed_value is False

    umb_text_2 = "Carry an umbrella if you are heading out."
    claims_u2 = extractor.extract_claims(umb_text_2)
    assert len(claims_u2) == 1
    assert claims_u2[0].variable == WeatherVariable.UMBRELLA_NEED
    assert claims_u2[0].claimed_value is True

    # 6. Test Non-factual / Opinion statements (should yield no claims)
    opinion_text = "I hope you have a wonderful and productive day ahead! Enjoy the beautiful day."
    claims_op = extractor.extract_claims(opinion_text)
    assert len(claims_op) == 0

    print("  -> Passed all ClaimExtractor unit tests.")


if __name__ == "__main__":
    test_claim_extractor()
