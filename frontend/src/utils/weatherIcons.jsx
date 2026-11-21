import {
  Sun,
  Moon,
  CloudSun,
  CloudMoon,
  Cloud,
  CloudFog,
  CloudDrizzle,
  CloudRain,
  CloudLightning,
  CloudSnow,
} from "lucide-react";

/**
 * WeatherIcon Component: Maps WMO code or condition string to a styled Lucide React SVG icon.
 */
export function WeatherIcon({
  weatherCode,
  condition = "",
  isNight = false,
  className = "weather-icon-svg",
}) {
  const cond = (condition || "").toLowerCase();
  const code = Number(weatherCode);

  // 0: Clear sky
  if (code === 0 || cond.includes("clear") || cond.includes("sunny")) {
    if (isNight) {
      return <Moon className={`${className} icon-night`} />;
    }
    return <Sun className={`${className} icon-sun`} />;
  }

  // 1, 2: Mainly clear, partly cloudy
  if (code === 1 || code === 2 || cond.includes("partly cloudy") || cond.includes("mainly clear")) {
    if (isNight) {
      return <CloudMoon className={`${className} icon-cloud-night`} />;
    }
    return <CloudSun className={`${className} icon-cloud-sun`} />;
  }

  // 3: Overcast
  if (code === 3 || cond.includes("overcast") || cond.includes("cloudy")) {
    return <Cloud className={`${className} icon-cloud`} />;
  }

  // 45, 48: Fog
  if (code === 45 || code === 48 || cond.includes("fog") || cond.includes("mist")) {
    return <CloudFog className={`${className} icon-fog`} />;
  }

  // 51, 53, 55, 56, 57: Drizzle
  if ((code >= 51 && code <= 57) || cond.includes("drizzle")) {
    return <CloudDrizzle className={`${className} icon-drizzle`} />;
  }

  // 61, 63, 65, 80, 81, 82: Rain / Showers
  if (
    (code >= 61 && code <= 67) ||
    (code >= 80 && code <= 82) ||
    cond.includes("rain") ||
    cond.includes("shower")
  ) {
    return <CloudRain className={`${className} icon-rain`} />;
  }

  // 71, 73, 75, 77, 85, 86: Snow
  if (
    (code >= 71 && code <= 77) ||
    code === 85 ||
    code === 86 ||
    cond.includes("snow") ||
    cond.includes("flurr")
  ) {
    return <CloudSnow className={`${className} icon-snow`} />;
  }

  // 95, 96, 99: Thunderstorm
  if ((code >= 95 && code <= 99) || cond.includes("thunder") || cond.includes("storm")) {
    return <CloudLightning className={`${className} icon-thunder`} />;
  }

  // Fallback
  return isNight ? (
    <CloudMoon className={`${className} icon-cloud-night`} />
  ) : (
    <CloudSun className={`${className} icon-cloud-sun`} />
  );
}
