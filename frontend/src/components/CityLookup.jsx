import { useState, useEffect, useRef } from "react";
import {
  Search,
  MapPin,
  Droplets,
  Wind,
  Compass,
  Gauge,
  Umbrella,
  CloudSun,
  Activity,
  Sparkles,
  Clock,
  ChevronRight,
  ChevronLeft,
  X,
  MessageSquare,
} from "lucide-react";
import { WeatherIcon } from "../utils/weatherIcons";

const API_BASE_URL = "http://127.0.0.1:8000";

export default function CityLookup({ onConsultAgent, onWeatherLoaded }) {
  const [location, setLocation] = useState("Dehradun");
  const [weather, setWeather] = useState(null);
  const [lookupError, setLookupError] = useState("");
  const [lookupLoading, setLookupLoading] = useState(false);
  const scrollContainerRef = useRef(null);

  const quickCities = [
    "Dehradun",
    "Tokyo",
    "London",
    "New York",
    "Paris",
    "Zurich",
    "Sydney",
  ];

  // Fetch weather for a given city query
  async function searchWeather(query) {
    const loc = (query !== undefined ? query : location).trim();
    if (!loc) {
      setLookupError("Please enter a city or region name.");
      return;
    }

    setLookupLoading(true);
    setLookupError("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/weather?location=${encodeURIComponent(loc)}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not retrieve weather data for this location.");
      }

      setWeather(data);
      setLocation(loc);
      if (onWeatherLoaded) {
        onWeatherLoaded(data);
      }
    } catch (err) {
      setLookupError(err.message || "Failed to retrieve meteorological data.");
    } finally {
      setLookupLoading(false);
    }
  }

  // Load initial city on mount
  useEffect(() => {
    let ignore = false;
    async function loadInitial() {
      setLookupLoading(true);
      try {
        const response = await fetch(
          `${API_BASE_URL}/weather?location=Dehradun`
        );
        const data = await response.json();
        if (!ignore && response.ok) {
          setWeather(data);
          if (onWeatherLoaded) {
            onWeatherLoaded(data);
          }
        }
      } catch (err) {
        if (!ignore) {
          setLookupError(err.message || "Failed to retrieve meteorological data.");
        }
      } finally {
        if (!ignore) {
          setLookupLoading(false);
        }
      }
    }
    loadInitial();
    return () => {
      ignore = true;
    };
  }, [onWeatherLoaded]);

  // Compute stats from forecast
  const forecastHours = weather?.forecast || [];
  let minTemp = null;
  let maxTemp = null;
  let maxRainProb = 0;

  if (forecastHours.length > 0) {
    const temps = forecastHours.map((h) => h.temperature);
    minTemp = Math.round(Math.min(...temps));
    maxTemp = Math.round(Math.max(...temps));

    forecastHours.slice(0, 24).forEach((h) => {
      if (h.precipitation_probability > maxRainProb) {
        maxRainProb = h.precipitation_probability;
      }
    });
  }

  // Wind cardinal direction
  const windDir = weather?.current?.wind_direction ?? 0;
  const windSpeed = weather?.current?.wind_speed ?? 0;

  // Beaufort scale helper
  const getBeaufortLabel = (speed) => {
    if (speed < 2) return "Calm";
    if (speed < 12) return "Light Breeze";
    if (speed < 20) return "Gentle Breeze";
    if (speed < 29) return "Moderate Breeze";
    if (speed < 39) return "Fresh Breeze";
    if (speed < 50) return "Strong Breeze";
    return "High Wind / Gale";
  };

  // Humidity comfort index
  const getHumidityComfort = (hum) => {
    if (hum < 30) return "Dry Air";
    if (hum <= 60) return "Optimal Comfort";
    if (hum <= 75) return "Moderate Humidity";
    return "High Moisture";
  };

  const handleScroll = (direction) => {
    if (scrollContainerRef.current) {
      const offset = direction === "left" ? -300 : 300;
      scrollContainerRef.current.scrollBy({ left: offset, behavior: "smooth" });
    }
  };

  return (
    <div className="city-dashboard-container">
      {/* Search Header Bar */}
      <div className="dashboard-search-card">
        <div className="dashboard-search-input-wrapper">
          <Search size={18} className="search-icon-svg" />
          <input
            type="text"
            className="dashboard-search-input"
            placeholder="Search any global city (e.g., Tokyo, London, Zurich, San Francisco)..."
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !lookupLoading) {
                searchWeather();
              }
            }}
            disabled={lookupLoading}
          />
          {location && (
            <button
              type="button"
              className="search-clear-btn"
              onClick={() => setLocation("")}
              title="Clear input"
            >
              <X size={15} />
            </button>
          )}
          <button
            type="button"
            className="dashboard-search-action-btn"
            onClick={() => searchWeather()}
            disabled={lookupLoading}
          >
            {lookupLoading ? "Locating..." : "Inspect Weather"}
          </button>
        </div>

        {/* Quick-Pick City Pills */}
        <div className="dashboard-quick-cities-row">
          <span className="quick-cities-label">Popular Centers:</span>
          <div className="quick-cities-pills">
            {quickCities.map((city) => (
              <button
                key={city}
                type="button"
                className={`quick-pill ${
                  weather?.location?.name?.toLowerCase().includes(city.toLowerCase())
                    ? "active"
                    : ""
                }`}
                onClick={() => searchWeather(city)}
                disabled={lookupLoading}
              >
                {city}
              </button>
            ))}
          </div>
        </div>

        {lookupError && (
          <div className="dashboard-error-banner" role="alert">
            <X size={16} />
            <span>{lookupError}</span>
          </div>
        )}
      </div>

      {/* Main Weather Visual Display */}
      {weather && weather.current && (
        <div className="dashboard-content-flow">
          {/* Top Hero Section */}
          <div className="dashboard-hero-card">
            <div className="hero-atmosphere-glow" />

            <div className="hero-top-meta">
              <div className="hero-location-block">
                <div className="location-name-row">
                  <MapPin size={22} className="location-pin-icon" />
                  <h2 className="location-name">{weather.location.name}</h2>
                </div>
                <span className="location-sub">
                  {[weather.location.region, weather.location.country]
                    .filter(Boolean)
                    .join(", ")}
                  {" • "}
                  {weather.location.latitude?.toFixed(2)}°N,{" "}
                  {weather.location.longitude?.toFixed(2)}°E
                </span>
              </div>

              {onConsultAgent && (
                <button
                  type="button"
                  className="consult-agent-hero-btn"
                  onClick={() =>
                    onConsultAgent(
                      `Provide a comprehensive meteorological briefing and travel recommendations for ${weather.location.name}.`
                    )
                  }
                  title="Switch to chat and consult AI Agent"
                >
                  <MessageSquare size={14} />
                  <span>Consult AI Agent</span>
                  <Sparkles size={13} className="sparkle-agent" />
                </button>
              )}
            </div>

            <div className="hero-middle-stats">
              <div className="hero-primary-temp-box">
                <div className="weather-animated-icon-display">
                  <WeatherIcon
                    weatherCode={weather.current.weather_code}
                    condition={weather.current.condition}
                    isNight={false}
                    className="hero-weather-icon-large"
                  />
                </div>
                <div className="temp-numbers">
                  <span className="main-temp-val">
                    {Math.round(weather.current.temperature)}°
                  </span>
                  <div className="temp-sub-details">
                    <span className="condition-badge">
                      {weather.current.condition}
                    </span>
                    <span className="feels-like-label">
                      Feels like {Math.round(weather.current.feels_like)}°C
                    </span>
                  </div>
                </div>
              </div>

              {minTemp !== null && maxTemp !== null && (
                <div className="hero-day-range-card">
                  <div className="range-item">
                    <span className="range-label">Day High</span>
                    <strong className="range-val text-amber">{maxTemp}°C</strong>
                  </div>
                  <div className="range-divider" />
                  <div className="range-item">
                    <span className="range-label">Day Low</span>
                    <strong className="range-val text-sky">{minTemp}°C</strong>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 24-Hour Hourly Forecast Slider */}
          {forecastHours.length > 0 && (
            <div className="hourly-forecast-section">
              <div className="section-header-row">
                <div className="header-title-box">
                  <Clock size={16} className="section-clock-icon" />
                  <h3 className="dashboard-section-title">24-Hour Hourly Timeline</h3>
                </div>
                <div className="slider-controls">
                  <button
                    type="button"
                    className="slider-arrow-btn"
                    onClick={() => handleScroll("left")}
                    aria-label="Scroll left"
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <button
                    type="button"
                    className="slider-arrow-btn"
                    onClick={() => handleScroll("right")}
                    aria-label="Scroll right"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>

              <div className="hourly-slider-container" ref={scrollContainerRef}>
                {forecastHours.slice(0, 24).map((hour, idx) => {
                  const hourTime = new Date(hour.time).toLocaleTimeString([], {
                    hour: "numeric",
                    minute: "2-digit",
                  });
                  const isCurrentHour = idx === 0;

                  return (
                    <div
                      key={hour.time || idx}
                      className={`hourly-card ${isCurrentHour ? "is-now" : ""}`}
                    >
                      <span className="hour-label">
                        {isCurrentHour ? "Now" : hourTime}
                      </span>
                      <div className="hour-icon-box">
                        <WeatherIcon
                          weatherCode={hour.weather_code}
                          condition={hour.condition}
                          isNight={false}
                          className="hour-weather-svg"
                        />
                      </div>
                      <span className="hour-temp">
                        {Math.round(hour.temperature)}°
                      </span>
                      <div className="hour-precip-badge">
                        <Droplets size={11} className="hour-precip-icon" />
                        <span>{Math.round(hour.precipitation_probability)}%</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Atmospheric Telemetry Grid */}
          <div className="telemetry-grid">
            {/* Humidity */}
            <div className="telemetry-card">
              <div className="telemetry-header">
                <span className="telemetry-label">Relative Humidity</span>
                <Droplets size={18} className="telemetry-icon text-cyan" />
              </div>
              <div className="telemetry-main">
                <strong className="telemetry-number">
                  {Math.round(weather.current.humidity)}%
                </strong>
                <span className="telemetry-status-pill">
                  {getHumidityComfort(weather.current.humidity)}
                </span>
              </div>
              <div className="telemetry-progress-track">
                <div
                  className="telemetry-progress-bar bg-cyan"
                  style={{ width: `${Math.min(weather.current.humidity, 100)}%` }}
                />
              </div>
            </div>

            {/* Wind Velocity & Compass */}
            <div className="telemetry-card">
              <div className="telemetry-header">
                <span className="telemetry-label">Wind Dynamics</span>
                <Wind size={18} className="telemetry-icon text-sky" />
              </div>
              <div className="telemetry-main wind-telemetry-main">
                <div>
                  <strong className="telemetry-number">
                    {weather.current.wind_speed?.toFixed(1)}{" "}
                    <span className="telemetry-unit">km/h</span>
                  </strong>
                  <span className="telemetry-status-pill">
                    {getBeaufortLabel(windSpeed)}
                  </span>
                </div>
                {weather.current.wind_direction !== null && (
                  <div
                    className="compass-indicator"
                    title={`Wind direction: ${windDir}°`}
                  >
                    <Compass
                      size={28}
                      className="compass-svg"
                      style={{ transform: `rotate(${windDir}deg)` }}
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Barometric Pressure */}
            <div className="telemetry-card">
              <div className="telemetry-header">
                <span className="telemetry-label">Surface Pressure</span>
                <Gauge size={18} className="telemetry-icon text-violet" />
              </div>
              <div className="telemetry-main">
                <strong className="telemetry-number">
                  {weather.current.pressure
                    ? Math.round(weather.current.pressure)
                    : "1013"}{" "}
                  <span className="telemetry-unit">hPa</span>
                </strong>
                <span className="telemetry-status-pill">
                  {weather.current.pressure && weather.current.pressure >= 1013
                    ? "High Pressure Front"
                    : "Low Pressure System"}
                </span>
              </div>
              <p className="telemetry-note">
                Mean sea level standard: 1013 hPa
              </p>
            </div>

            {/* Cloud Cover */}
            <div className="telemetry-card">
              <div className="telemetry-header">
                <span className="telemetry-label">Cloud Cover</span>
                <CloudSun size={18} className="telemetry-icon text-amber" />
              </div>
              <div className="telemetry-main">
                <strong className="telemetry-number">
                  {weather.current.cloud_cover !== null &&
                  weather.current.cloud_cover !== undefined
                    ? Math.round(weather.current.cloud_cover)
                    : 25}
                  %
                </strong>
                <span className="telemetry-status-pill">
                  {weather.current.cloud_cover > 75
                    ? "Dense Overcast"
                    : weather.current.cloud_cover > 30
                    ? "Scattered Clouds"
                    : "Clear Sky"}
                </span>
              </div>
              <div className="telemetry-progress-track">
                <div
                  className="telemetry-progress-bar bg-amber"
                  style={{
                    width: `${Math.min(
                      weather.current.cloud_cover || 25,
                      100
                    )}%`,
                  }}
                />
              </div>
            </div>
          </div>

          {/* Decision Support Banner Cards */}
          <div className="decision-support-row">
            {/* Umbrella Check */}
            <div
              className={`decision-card ${
                maxRainProb > 30 ? "action-advised" : "action-clear"
              }`}
            >
              <div className="decision-icon-box">
                <Umbrella size={22} />
              </div>
              <div className="decision-body">
                <h4 className="decision-title">
                  {maxRainProb > 30 ? "Umbrella Recommended" : "No Umbrella Needed"}
                </h4>
                <p className="decision-desc">
                  {maxRainProb > 30
                    ? `Peak rain probability of ${Math.round(
                        maxRainProb
                      )}% anticipated over the next 24 hours.`
                    : "Precipitation risk remains under 30% throughout the coming day."}
                </p>
              </div>
            </div>

            {/* Outdoor Window */}
            <div className="decision-card action-window">
              <div className="decision-icon-box">
                <Activity size={22} />
              </div>
              <div className="decision-body">
                <h4 className="decision-title">Outdoor Comfort Index</h4>
                <p className="decision-desc">
                  {weather.current.temperature >= 15 &&
                  weather.current.temperature <= 26 &&
                  windSpeed < 25
                    ? "Excellent meteorological conditions for outdoor recreation and travel."
                    : "Plan outdoor activities around peak diurnal temperature windows."}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
