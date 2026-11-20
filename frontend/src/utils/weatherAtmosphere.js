/**
 * Determines the ambient weather scene from meteorological metrics and conditions.
 * Returns: 'sun' | 'rain' | 'stars' | 'wind' | 'snow' | 'thunder' | 'clouds'
 */
export function detectWeatherScene({
  weatherCode,
  condition = "",
  windSpeed = 0,
  isNight = false,
}) {
  const cond = (condition || "").toLowerCase();
  const code = Number(weatherCode);

  // Thunderstorm
  if (
    (code >= 95 && code <= 99) ||
    cond.includes("thunder") ||
    cond.includes("storm") ||
    cond.includes("lightning")
  ) {
    return "thunder";
  }

  // Snow
  if (
    (code >= 71 && code <= 77) ||
    code === 85 ||
    code === 86 ||
    cond.includes("snow") ||
    cond.includes("flurr") ||
    cond.includes("blizzard") ||
    cond.includes("sleet")
  ) {
    return "snow";
  }

  // Rain / Showers / Drizzle
  if (
    (code >= 51 && code <= 67) ||
    (code >= 80 && code <= 82) ||
    cond.includes("rain") ||
    cond.includes("shower") ||
    cond.includes("drizzle")
  ) {
    return "rain";
  }

  // Strong wind / breezy (leaves blowing!)
  if (windSpeed >= 18 || cond.includes("wind") || cond.includes("breeze") || cond.includes("gale")) {
    return "wind";
  }

  // Night with clear / mostly clear skies -> Stars
  if (isNight && (code === 0 || code === 1 || code === 2 || cond.includes("clear"))) {
    return "stars";
  }

  // Daytime clear / sunny -> Sunshine
  if (!isNight && (code === 0 || code === 1 || cond.includes("clear") || cond.includes("sun"))) {
    return "sun";
  }

  // Overcast / Cloudy / Fog
  if (
    code === 3 ||
    code === 45 ||
    code === 48 ||
    cond.includes("cloud") ||
    cond.includes("overcast") ||
    cond.includes("fog") ||
    cond.includes("mist")
  ) {
    return "clouds";
  }

  // Default fallback based on day/night
  return isNight ? "stars" : "sun";
}

export const WEATHER_SCENES = [
  { id: "auto", label: "Auto (Live Weather)", icon: "🌦️" },
  { id: "sun", label: "Sunshine", icon: "☀️" },
  { id: "rain", label: "Rain Shower", icon: "🌧️" },
  { id: "stars", label: "Midnight Stars", icon: "🌌" },
  { id: "wind", label: "Wind & Leaves", icon: "🍃" },
  { id: "snow", label: "Falling Snow", icon: "❄️" },
  { id: "thunder", label: "Thunderstorm", icon: "⛈️" },
  { id: "clouds", label: "Soft Clouds", icon: "☁️" },
];
