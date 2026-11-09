import { useState } from "react";

const API_BASE_URL = "http://127.0.0.1:8000";

export default function CityLookup() {
  const [location, setLocation] = useState("");
  const [weather, setWeather] = useState(null);
  const [lookupError, setLookupError] = useState("");
  const [lookupLoading, setLookupLoading] = useState(false);

  async function searchWeather() {
    const loc = location.trim();
    if (!loc) {
      setLookupError("Please enter a city name.");
      return;
    }

    setLookupLoading(true);
    setLookupError("");
    setWeather(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/weather?location=${encodeURIComponent(loc)}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not fetch weather data.");
      }

      setWeather(data);
    } catch (err) {
      setLookupError(err.message || "Failed to retrieve weather.");
    } finally {
      setLookupLoading(false);
    }
  }

  return (
    <div className="city-lookup-container">
      <div className="search-box">
        <input
          type="text"
          placeholder="Enter a city name (e.g. Dehradun, Tokyo, Paris)..."
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !lookupLoading) {
              searchWeather();
            }
          }}
          disabled={lookupLoading}
        />
        <button type="button" onClick={searchWeather} disabled={lookupLoading}>
          {lookupLoading ? "Searching..." : "Search"}
        </button>
      </div>

      {lookupError && <div className="error">⚠️ {lookupError}</div>}

      {weather && (
        <div className="weather-card">
          <div className="location">
            <h2>{weather.location.name}</h2>
            <p>
              {weather.location.region ? `${weather.location.region}, ` : ""}
              {weather.location.country}
            </p>
          </div>

          <div className="temperature">{weather.current.temperature}°C</div>
          <div className="condition">
            <span className="condition-icon">{weather.current.icon}</span>
            <span>{weather.current.condition}</span>
          </div>

          <div className="weather-details">
            <div className="detail">
              <span>🌡️</span>
              <p>Feels like</p>
              <strong>{weather.current.feels_like}°C</strong>
            </div>

            <div className="detail">
              <span>💧</span>
              <p>Humidity</p>
              <strong>{weather.current.humidity}%</strong>
            </div>

            <div className="detail">
              <span>💨</span>
              <p>Wind</p>
              <strong>{weather.current.wind_speed} km/h</strong>
            </div>
          </div>

          {weather.forecast && weather.forecast.length > 0 && (
            <div className="forecast-section">
              <h3>Next 24 Hours</h3>
              <div className="forecast-list">
                {weather.forecast.map((hour) => (
                  <div className="forecast-item" key={hour.time}>
                    <span className="forecast-time">
                      {new Date(hour.time).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    <span className="forecast-icon">{hour.icon}</span>
                    <span className="forecast-temperature">
                      {hour.temperature}°C
                    </span>
                    <span className="forecast-condition">
                      {hour.condition}
                    </span>
                    <span className="forecast-rain">
                      🌧️ {hour.precipitation_probability}%
                    </span>
                    <span className="forecast-wind">
                      💨 {hour.wind_speed} km/h
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="updated">Observation time: {weather.current.time}</div>
        </div>
      )}
    </div>
  );
}
