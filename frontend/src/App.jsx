import { useState } from "react";
import "./App.css";

function App() {
  const [location, setLocation] = useState("");
  const [weather, setWeather] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function searchWeather() {
    if (!location.trim()) {
      setError("Please enter a city name.");
      return;
    }

    setLoading(true);
    setError("");
    setWeather(null);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/weather?location=${encodeURIComponent(
          location
        )}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not fetch weather.");
      }

      setWeather(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <div className="container">

        <header className="header">
          <h1>🌦️ WeatherGPT</h1>
          <p>Ask about the weather anywhere.</p>
        </header>

        <div className="search-box">
          <input
            type="text"
            placeholder="Enter a city..."
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                searchWeather();
              }
            }}
          />

          <button onClick={searchWeather} disabled={loading}>
            {loading ? "Searching..." : "Search"}
          </button>
        </div>

        {error && (
          <div className="error">
            ⚠️ {error}
          </div>
        )}

        {weather && (
          <div className="weather-card">

            {/* Location */}
            <div className="location">
              <h2>
                {weather.location.name}
              </h2>

              <p>
                {weather.location.region},{" "}
                {weather.location.country}
              </p>
            </div>


            {/* Current temperature */}
            <div className="temperature">
              {weather.current.temperature}°C
            </div>
            <div className="condition">
              <span className="condition-icon">
                {weather.current.icon}
              </span>

              <span>
                {weather.current.condition}
              </span>
            </div>


            {/* Current weather details */}
            <div className="weather-details">

              <div className="detail">
                <span>🌡️</span>
                <p>Feels like</p>
                <strong>
                  {weather.current.feels_like}°C
                </strong>
              </div>

              <div className="detail">
                <span>💧</span>
                <p>Humidity</p>
                <strong>
                  {weather.current.humidity}%
                </strong>
              </div>

              <div className="detail">
                <span>💨</span>
                <p>Wind</p>
                <strong>
                  {weather.current.wind_speed} km/h
                </strong>
              </div>

            </div>


            {/* 24 hour forecast */}
            <div className="forecast-section">

              <h3>Next 24 Hours</h3>

              <div className="forecast-list">

                {weather.forecast.map((hour) => (
                  <div
                    className="forecast-item"
                    key={hour.time}
                  >
                    <span className="forecast-time">
                      {new Date(hour.time).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>

                    <span className="forecast-icon">
                      {hour.icon}
                    </span>

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


            {/* Last updated */}
            <div className="updated">
              Updated: {weather.current.time}
            </div>

          </div>
        )}

      </div>
    </div>
  );
}

export default App;