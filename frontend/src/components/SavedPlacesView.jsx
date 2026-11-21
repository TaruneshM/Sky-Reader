import { useState, useEffect } from "react";
import {
  Bookmark,
  Plus,
  Trash2,
  Compass,
  MessageSquare,
  MapPin,
  RefreshCw,
  Search,
  Droplets,
  Wind,
} from "lucide-react";
import { WeatherIcon } from "../utils/weatherIcons";

const API_BASE_URL = "http://127.0.0.1:8000";

export default function SavedPlacesView({
  savedCities = [],
  onAddCity,
  onRemoveCity,
  onSelectCity,
  onConsultAgent,
}) {
  const [cityInput, setCityInput] = useState("");
  const [weatherMap, setWeatherMap] = useState({});
  const [loadingMap, setLoadingMap] = useState({});
  const [errorMap, setErrorMap] = useState({});
  const [isAdding, setIsAdding] = useState(false);
  const [addError, setAddError] = useState("");

  const suggestedCities = [
    "Tokyo",
    "Zurich",
    "London",
    "New York",
    "Paris",
    "Reykjavik",
    "Sydney",
    "Dehradun",
  ];

  // Fetch weather for all saved cities
  useEffect(() => {
    let isCancelled = false;

    savedCities.forEach((city) => {
      if (!weatherMap[city] && !loadingMap[city]) {
        setLoadingMap((prev) => ({ ...prev, [city]: true }));
        fetch(`${API_BASE_URL}/weather?location=${encodeURIComponent(city)}`)
          .then((res) => {
            if (!res.ok) throw new Error("Unavailable");
            return res.json();
          })
          .then((data) => {
            if (!isCancelled) {
              setWeatherMap((prev) => ({ ...prev, [city]: data }));
              setLoadingMap((prev) => ({ ...prev, [city]: false }));
            }
          })
          .catch(() => {
            if (!isCancelled) {
              setErrorMap((prev) => ({ ...prev, [city]: true }));
              setLoadingMap((prev) => ({ ...prev, [city]: false }));
            }
          });
      }
    });

    return () => {
      isCancelled = true;
    };
  }, [savedCities, weatherMap, loadingMap]);

  const handleAddSubmit = async (e) => {
    e.preventDefault();
    const clean = cityInput.trim();
    if (!clean) return;

    if (savedCities.some((c) => c.toLowerCase() === clean.toLowerCase())) {
      setAddError(`"${clean}" is already in your saved places.`);
      return;
    }

    setAddError("");
    setIsAdding(true);

    try {
      // Validate city exists via weather API
      const res = await fetch(`${API_BASE_URL}/weather?location=${encodeURIComponent(clean)}`);
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || `Location "${clean}" could not be resolved.`);
      }

      const canonicalName = data.location?.name || clean;
      onAddCity(canonicalName);
      setWeatherMap((prev) => ({ ...prev, [canonicalName]: data }));
      setCityInput("");
    } catch (err) {
      setAddError(err.message || "Failed to find location. Please check the spelling.");
    } finally {
      setIsAdding(false);
    }
  };

  const handleQuickAdd = (city) => {
    if (!savedCities.some((c) => c.toLowerCase() === city.toLowerCase())) {
      onAddCity(city);
    }
  };

  const refreshCityWeather = (city, e) => {
    e.stopPropagation();
    setLoadingMap((prev) => ({ ...prev, [city]: true }));
    setErrorMap((prev) => ({ ...prev, [city]: false }));

    fetch(`${API_BASE_URL}/weather?location=${encodeURIComponent(city)}`)
      .then((res) => {
        if (!res.ok) throw new Error("Unavailable");
        return res.json();
      })
      .then((data) => {
        setWeatherMap((prev) => ({ ...prev, [city]: data }));
        setLoadingMap((prev) => ({ ...prev, [city]: false }));
      })
      .catch(() => {
        setErrorMap((prev) => ({ ...prev, [city]: true }));
        setLoadingMap((prev) => ({ ...prev, [city]: false }));
      });
  };

  return (
    <div className="saved-places-container">
      {/* Header Banner */}
      <div className="saved-places-header">
        <div className="saved-header-title-box">
          <div className="saved-title-icon-badge">
            <Bookmark size={20} />
          </div>
          <div className="saved-title-meta">
            <h1 className="saved-main-heading">Saved Places</h1>
            <p className="saved-sub-heading">
              Manage your personal atmospheric watchlist with instant real-time telemetry and AI briefings.
            </p>
          </div>
        </div>

        {/* Add City Bar */}
        <form className="saved-add-bar-form" onSubmit={handleAddSubmit}>
          <div className="saved-add-input-wrapper">
            <Search size={15} className="saved-search-icon" />
            <input
              type="text"
              className="saved-city-input"
              placeholder="Add any global city (e.g. Kyoto, Vancouver, Rome)..."
              value={cityInput}
              onChange={(e) => {
                setCityInput(e.target.value);
                setAddError("");
              }}
            />
          </div>
          <button
            type="submit"
            className="saved-add-btn"
            disabled={isAdding || !cityInput.trim()}
          >
            {isAdding ? (
              <span>Checking...</span>
            ) : (
              <>
                <Plus size={15} />
                <span>Save Place</span>
              </>
            )}
          </button>
        </form>
      </div>

      {addError && (
        <div className="saved-add-error-pill" role="alert">
          <span>{addError}</span>
        </div>
      )}

      {/* Suggested Quick Add Chips */}
      <div className="saved-quick-suggestions">
        <span className="suggestions-chip-label">Quick Add:</span>
        <div className="suggestions-chip-row">
          {suggestedCities
            .filter((c) => !savedCities.some((sc) => sc.toLowerCase() === c.toLowerCase()))
            .slice(0, 6)
            .map((c) => (
              <button
                key={c}
                type="button"
                className="saved-quick-chip"
                onClick={() => handleQuickAdd(c)}
                title={`Add ${c} to your saved places`}
              >
                <Plus size={11} />
                <span>{c}</span>
              </button>
            ))}
        </div>
      </div>

      {/* Empty State */}
      {savedCities.length === 0 ? (
        <div className="saved-places-empty-state">
          <div className="empty-state-icon-box">
            <Bookmark size={36} />
          </div>
          <h2 className="empty-state-title">No Saved Places Yet</h2>
          <p className="empty-state-desc">
            Bookmark your favorite cities or travel destinations to track them side-by-side with live telemetry.
          </p>
          <div className="empty-state-buttons">
            {suggestedCities.slice(0, 4).map((c) => (
              <button
                key={c}
                type="button"
                className="empty-starter-pill"
                onClick={() => handleQuickAdd(c)}
              >
                <Plus size={13} />
                <span>Add {c}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        /* Saved Cities Cards Grid */
        <div className="saved-cards-grid">
          {savedCities.map((city) => {
            const data = weatherMap[city];
            const isLoading = loadingMap[city];
            const isErr = errorMap[city];

            const current = data?.current;
            const location = data?.location;

            return (
              <div
                key={city}
                className="saved-city-card"
                onClick={() => onSelectCity(city)}
                title={`Click to open full forecast for ${city}`}
              >
                {/* Top Row: Location & Actions */}
                <div className="saved-card-top-row">
                  <div className="saved-card-location-meta">
                    <div className="saved-location-name-row">
                      <MapPin size={15} className="saved-pin-icon" />
                      <h3 className="saved-card-city-name">{location?.name || city}</h3>
                    </div>
                    <span className="saved-card-region">
                      {location?.country || "Global Observation Point"}
                    </span>
                  </div>

                  <div className="saved-card-actions" onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      className="saved-card-icon-btn refresh-btn"
                      onClick={(e) => refreshCityWeather(city, e)}
                      title="Refresh weather"
                    >
                      <RefreshCw size={13} className={isLoading ? "spin-icon" : ""} />
                    </button>
                    <button
                      type="button"
                      className="saved-card-icon-btn delete-btn"
                      onClick={() => onRemoveCity(city)}
                      title={`Remove ${city} from saved places`}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>

                {/* Middle: Weather details */}
                {isLoading && !current ? (
                  <div className="saved-card-loading">
                    <div className="saved-loading-spinner" />
                    <span>Loading atmospheric telemetry...</span>
                  </div>
                ) : isErr ? (
                  <div className="saved-card-error">
                    <span>Telemetry temporarily unavailable</span>
                    <button
                      type="button"
                      className="saved-retry-btn"
                      onClick={(e) => refreshCityWeather(city, e)}
                    >
                      Retry
                    </button>
                  </div>
                ) : current ? (
                  <>
                    <div className="saved-card-main-weather">
                      <div className="saved-card-temp-box">
                        <span className="saved-card-temp">
                          {Math.round(current.temperature)}°
                        </span>
                        <div className="saved-card-condition-meta">
                          <span className="saved-card-condition">{current.condition}</span>
                          <span className="saved-card-feels">
                            Feels like {Math.round(current.apparent_temperature)}°
                          </span>
                        </div>
                      </div>

                      <div className="saved-card-weather-icon-box">
                        <WeatherIcon
                          weatherCode={current.weather_code}
                          size={38}
                          className="saved-weather-icon"
                        />
                      </div>
                    </div>

                    <div className="saved-card-telemetry-row">
                      <div className="saved-telemetry-badge">
                        <Droplets size={12} className="telemetry-sub-icon humidity" />
                        <span>{current.relative_humidity}% Hum</span>
                      </div>
                      <div className="saved-telemetry-badge">
                        <Wind size={12} className="telemetry-sub-icon wind" />
                        <span>{Math.round(current.wind_speed)} km/h</span>
                      </div>
                      {current.is_day === 1 ? (
                        <div className="saved-telemetry-badge day">☀️ Daytime</div>
                      ) : (
                        <div className="saved-telemetry-badge night">🌙 Night</div>
                      )}
                    </div>
                  </>
                ) : null}

                {/* Bottom Row Action Buttons */}
                <div
                  className="saved-card-footer-actions"
                  onClick={(e) => e.stopPropagation()}
                >
                  <button
                    type="button"
                    className="saved-footer-btn view-dash"
                    onClick={() => onSelectCity(city)}
                  >
                    <Compass size={13} />
                    <span>Dashboard & Trips</span>
                  </button>

                  <button
                    type="button"
                    className="saved-footer-btn ask-agent"
                    onClick={() =>
                      onConsultAgent(`What is the meteorological forecast and travel recommendation for ${city}?`)
                    }
                  >
                    <MessageSquare size={13} />
                    <span>Ask AI</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
