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
    <div className="weather-snapshot-grid">
      {tempVal && (
        <div className="snapshot-card temp">
          <span className="snapshot-icon">🌡️</span>
          <div className="snapshot-info">
            <span className="snapshot-label">Temperature</span>
            <strong className="snapshot-value">{tempVal}</strong>
            {feelsClaim && (
              <span className="snapshot-sub">Feels {feelsClaim.claimed_value}°C</span>
            )}
          </div>
        </div>
      )}

      {humVal && (
        <div className="snapshot-card humidity">
          <span className="snapshot-icon">💧</span>
          <div className="snapshot-info">
            <span className="snapshot-label">Humidity</span>
            <strong className="snapshot-value">{humVal}</strong>
          </div>
        </div>
      )}

      {windVal && (
        <div className="snapshot-card wind">
          <span className="snapshot-icon">💨</span>
          <div className="snapshot-info">
            <span className="snapshot-label">Wind Speed</span>
            <strong className="snapshot-value">{windVal}</strong>
          </div>
        </div>
      )}

      {rainVal && (
        <div className="snapshot-card rain">
          <span className="snapshot-icon">🌧️</span>
          <div className="snapshot-info">
            <span className="snapshot-label">Rain Chance</span>
            <strong className="snapshot-value">{rainVal}</strong>
            {rainAmtClaim && (
              <span className="snapshot-sub">{rainAmtClaim.claimed_value} mm</span>
            )}
          </div>
        </div>
      )}

      {umbrellaClaim && (
        <div
          className={`snapshot-card umbrella ${
            umbrellaClaim.claimed_value ? "recommended" : "not-needed"
          }`}
        >
          <span className="snapshot-icon">☔</span>
          <div className="snapshot-info">
            <span className="snapshot-label">Umbrella</span>
            <strong className="snapshot-value">
              {umbrellaClaim.claimed_value ? "Carry One" : "Not Needed"}
            </strong>
          </div>
        </div>
      )}
    </div>
  );
}
