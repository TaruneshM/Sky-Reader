import { useState, useRef, useEffect } from "react";
import { Sparkles, ChevronDown } from "lucide-react";
import { WEATHER_SCENES } from "../utils/weatherAtmosphere";

export default function AtmosphereSelector({
  selectedMode,
  onSelectMode,
  activeScene,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  // Close when clicking outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const currentItem =
    WEATHER_SCENES.find((s) => s.id === selectedMode) || WEATHER_SCENES[0];
  const activeSceneItem =
    WEATHER_SCENES.find((s) => s.id === activeScene) || WEATHER_SCENES[1];

  return (
    <div className="atmosphere-selector-container" ref={containerRef}>
      <button
        type="button"
        className="atmosphere-pill-btn"
        onClick={() => setIsOpen((prev) => !prev)}
        title="Change ambient weather animation (Rain, Sunshine, Stars, Wind, Snow...)"
        aria-expanded={isOpen}
      >
        <span className="atmosphere-active-icon">
          {selectedMode === "auto" ? activeSceneItem.icon : currentItem.icon}
        </span>
        <span className="atmosphere-active-label">
          {selectedMode === "auto" ? `Auto: ${activeSceneItem.label}` : currentItem.label}
        </span>
        <ChevronDown size={13} className={`chevron-icon ${isOpen ? "rotate" : ""}`} />
      </button>

      {isOpen && (
        <div className="atmosphere-dropdown-menu">
          <div className="dropdown-header">
            <Sparkles size={13} className="sparkle-menu-icon" />
            <span>Atmospheric Simulation</span>
          </div>

          <div className="dropdown-items-list">
            {WEATHER_SCENES.map((scene) => {
              const isSelected = selectedMode === scene.id;
              return (
                <button
                  key={scene.id}
                  type="button"
                  className={`dropdown-scene-btn ${isSelected ? "selected" : ""}`}
                  onClick={() => {
                    onSelectMode(scene.id);
                    setIsOpen(false);
                  }}
                >
                  <span className="scene-btn-icon">{scene.icon}</span>
                  <span className="scene-btn-label">{scene.label}</span>
                  {isSelected && <span className="scene-active-bullet" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
