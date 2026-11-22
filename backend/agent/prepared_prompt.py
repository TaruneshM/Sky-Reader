"""Model-facing representation of planner evidence. Audits use original source data."""
from .llm_budget import encode_wire


HOURLY_FIELDS = {
    "temperature_2m": "temperature_c", "apparent_temperature": "feels_like_c",
    "relative_humidity_2m": "humidity_pct", "precipitation_probability": "rain_probability_pct",
    "precipitation": "precipitation_mm", "wind_speed_10m": "wind_kmh",
    "wind_gusts_10m": "gust_kmh", "weather_code": "wmo_code",
}


def synthesis_message(destinations, risks, components, activity, *, hourly_detail=False):
    packets = []
    for destination, risk in zip(destinations, risks, strict=True):
        raw = destination.data()
        place = destination.place
        packet = {
            "place": [value for value in (place.name, place.region, place.country) if value],
            "timezone": place.timezone or raw.get("timezone"), "period": destination.period,
            "source": "Open-Meteo", "kind": "forecast" if destination.requirement == "hourly" else "observation",
            "status": destination.status,
        }
        if destination.requirement == "hourly":
            hourly = raw.get("hourly", {})
            times = hourly.get("time", [])
            if times:
                packet["local_window"] = [times[0], times[-1]]
                packet["forecast_hours"] = len(times)
                values = {}
                for field, label in HOURLY_FIELDS.items():
                    series = hourly.get(field, [])
                    if len(series) == len(times) and all(type(value) in (int, float) for value in series):
                        values[label] = series if hourly_detail else [min(series), max(series)]
                    elif hourly_detail and len(series) == len(times) and all(
                        value is None or type(value) in (int, float) for value in series
                    ):
                        values[label] = series
                packet["hourly_from_start"] = values if hourly_detail else None
                if not hourly_detail:
                    packet.pop("hourly_from_start")
                    packet["range_min_max"] = values
        else:
            current = raw.get("current", {})
            packet["local_time"] = current.get("time")
            packet["observed"] = {label: current[field] for field, label in HOURLY_FIELDS.items()
                                  if current.get(field) is not None}
        if risk:
            packet["risk"] = {
                "level": risk["overall_risk_level"],
                "hazards": [
                    {"condition": item["condition"], "severity": item["severity"],
                     "guidance": item["recommendations"][:1]}
                    for item in risk["detected_risks"]
                ],
                "limitations": risk["data_limitations"],
            }
        packets.append(packet)
    return {
        "role": "system",
        "content": (
            "Verified planned weather data. Answer using only these scoped sources. "
            "Name the place and local period for each factual claim. Keep cities and periods separate. "
            "Treat absent values as unavailable, forecasts as uncertain, and preserve material hazards. "
            "State limitations. Do not request tools. "
            + encode_wire({"requested": list(components), "activity": activity, "weather": packets})[0]
        ),
    }
