import {
  Thermometer,
  Droplets,
  Wind,
  CloudRain,
  Umbrella,
  CheckCircle2,
  XCircle,
  TrendingUp,
} from "lucide-react";

export default function WeatherSnapshot({ claims = [], text = "" }) {
  // Extract key metrics from actual backend claims if available
  const tempClaim = claims.find(
    (c) => c.variable === "temperature" && typeof c.claimed_value === "number"
  );
  const feelsClaim = claims.find(
    (c) => c.variable === "apparent_temperature" && typeof c.claimed_value === "number"
  );
  const humClaim = claims.find(
    (c) => c.variable === "humidity" && typeof c.claimed_value === "number"
  );
  const rainClaim = claims.find(
    (c) => c.variable === "precipitation_probability" && typeof c.claimed_value === "number"
  );
  const rainAmtClaim = claims.find(
    (c) => c.variable === "precipitation_amount" && typeof c.claimed_value === "number"
  );
  const windClaim = claims.find(
    (c) => c.variable === "wind_speed" && typeof c.claimed_value === "number"
  );
  const umbrellaClaim = claims.find((c) => c.variable === "umbrella_need");

  // Fallback pattern matching on text if claims array is empty
  let tempVal = tempClaim ? `${tempClaim.claimed_value}°C` : null;
  let humVal = humClaim ? `${humClaim.claimed_value}%` : null;
  let windVal = windClaim ? `${windClaim.claimed_value} km/h` : null;
  let rainVal = rainClaim ? `${rainClaim.claimed_value}%` : null;

  if (!tempVal) {
    const m = text.match(/(-?\d+(?:\.\d+)?)\s*(?:°\s*C|degrees?\s*celsius)/i);
    if (m) tempVal = `${m[1]}°C`;
  }
  if (!humVal) {
    const m = text.match(/humidity\D*?(\d+(?:\.\d+)?)\s*%/i);
    if (m) humVal = `${m[1]}%`;
  }
  if (!windVal) {
    const m = text.match(/(\d+(?:\.\d+)?)\s*km\/h/i);
    if (m) windVal = `${m[1]} km/h`;
  }
  if (!rainVal) {
    const m = text.match(/(\d+(?:\.\d+)?)\s*%\s*(?:chance|probability)/i);
    if (m) rainVal = `${m[1]}%`;
  }

  const hasMetrics = tempVal || humVal || windVal || rainVal || umbrellaClaim;
  if (!hasMetrics) return null;

  return (
    <div className="weather-snapshot-container">
      <div className="snapshot-header-label">
        <TrendingUp size={13} className="snapshot-trend-icon" />
        <span>Meteorological Telemetry</span>
      </div>

      <div className="weather-snapshot-grid">
        {/* Temperature Card */}
        {tempVal && (
          <div className="snapshot-card temp-card">
            <div className="snapshot-icon-wrapper temp-icon-bg">
              <Thermometer size={18} />
            </div>
            <div className="snapshot-info">
              <span className="snapshot-label">Temperature</span>
              <strong className="snapshot-value">{tempVal}</strong>
              {feelsClaim && (
                <span className="snapshot-sub">Feels {feelsClaim.claimed_value}°C</span>
              )}
            </div>
          </div>
        )}

        {/* Humidity Card */}
        {humVal && (
          <div className="snapshot-card humidity-card">
            <div className="snapshot-icon-wrapper hum-icon-bg">
              <Droplets size={18} />
            </div>
            <div className="snapshot-info">
              <span className="snapshot-label">Relative Humidity</span>
              <strong className="snapshot-value">{humVal}</strong>
            </div>
          </div>
        )}

        {/* Wind Speed Card */}
        {windVal && (
          <div className="snapshot-card wind-card">
            <div className="snapshot-icon-wrapper wind-icon-bg">
              <Wind size={18} />
            </div>
            <div className="snapshot-info">
              <span className="snapshot-label">Wind Velocity</span>
              <strong className="snapshot-value">{windVal}</strong>
            </div>
          </div>
        )}

        {/* Rain Probability Card */}
        {rainVal && (
          <div className="snapshot-card rain-card">
            <div className="snapshot-icon-wrapper rain-icon-bg">
              <CloudRain size={18} />
            </div>
            <div className="snapshot-info">
              <span className="snapshot-label">Precipitation Chance</span>
              <strong className="snapshot-value">{rainVal}</strong>
              {rainAmtClaim && (
                <span className="snapshot-sub">{rainAmtClaim.claimed_value} mm volume</span>
              )}
            </div>
          </div>
        )}

        {/* Umbrella Recommendation Card */}
        {umbrellaClaim && (
          <div
            className={`snapshot-card umbrella-card ${
              umbrellaClaim.claimed_value ? "recommended" : "not-needed"
            }`}
          >
            <div className="snapshot-icon-wrapper umbrella-icon-bg">
              <Umbrella size={18} />
            </div>
            <div className="snapshot-info">
              <span className="snapshot-label">Umbrella Advisory</span>
              <div className="umbrella-decision-tag">
                {umbrellaClaim.claimed_value ? (
                  <>
                    <CheckCircle2 size={13} className="advisory-check" />
                    <strong>Recommended</strong>
                  </>
                ) : (
                  <>
                    <XCircle size={13} className="advisory-cross" />
                    <strong>Not Required</strong>
                  </>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
