import { useState } from "react";
import {
  SlidersHorizontal,
  ArrowUp,
  DollarSign,
  Mountain,
  Coffee,
  Compass,
} from "lucide-react";

export default function WelcomeHero({ onSelectPrompt, onSendQuery }) {
  const [heroInput, setHeroInput] = useState("");

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && heroInput.trim()) {
      e.preventDefault();
      if (onSendQuery) {
        onSendQuery(heroInput.trim());
      } else {
        onSelectPrompt(heroInput.trim());
      }
    }
  };

  const handleSendClick = () => {
    if (heroInput.trim()) {
      if (onSendQuery) {
        onSendQuery(heroInput.trim());
      } else {
        onSelectPrompt(heroInput.trim());
      }
    }
  };

  const starterCards = [
    {
      title: "A 7-day island escape under $1000",
      query: "Plan a 7-day island escape under $1000 with real-time sunny weather and flight advice",
      icon: <DollarSign size={15} />,
    },
    {
      title: "A 3-day hiking trip with flora stays",
      query: "Find the best 3-day hiking trip with pleasant weather conditions and flora stays",
      icon: <Mountain size={15} />,
    },
    {
      title: "A weekend art & coffee tour in Tokyo",
      query: "What is the weekend weather outlook for an art and coffee tour in Tokyo?",
      icon: <Coffee size={15} />,
    },
    {
      title: "A slow travel journey across Europe",
      query: "Check weather trends and travel advisories for a slow journey across Europe",
      icon: <Compass size={15} />,
    },
  ];

  return (
    <div className="welcome-hero-container">
      {/* Centered Glowing Amber-Orange Circular Badge (Matches Video 1) */}
      <div className="hero-amber-brand-emblem">
        <div className="amber-emblem-core">
          <span className="amber-emblem-icon">▲</span>
        </div>
      </div>

      {/* Main Headline */}
      <h1 className="welcome-hero-title">
        What Can I Help You Plan Today?
      </h1>

      {/* Subtitle */}
      <p className="welcome-hero-subtitle">
        Sky Reader helps you create custom travel itineraries &amp; meteorological forecasts based on your interests, budget, and time — instantly.
      </p>

      {/* Central Input Box (Matches Video 1) */}
      <div className="hero-center-input-capsule">
        <button
          type="button"
          className="capsule-filter-icon-btn"
          title="Filter and Preferences"
          aria-label="Filter preferences"
        >
          <SlidersHorizontal size={15} />
        </button>

        <input
          type="text"
          className="hero-capsule-input-field"
          placeholder="Ex: Plan a romantic 5-day trip to Paris this November"
          value={heroInput}
          onChange={(e) => setHeroInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />

        <button
          type="button"
          className={`capsule-send-btn ${heroInput.trim() ? "has-text" : ""}`}
          onClick={handleSendClick}
          disabled={!heroInput.trim()}
          title="Send query"
          aria-label="Send query"
        >
          <ArrowUp size={16} />
        </button>
      </div>

      {/* 2x2 Suggested Cards Grid (Matches Video 1) */}
      <div className="starter-prompts-grid-video1">
        {starterCards.map((card, idx) => (
          <button
            key={idx}
            type="button"
            className="video1-starter-card"
            onClick={() => onSelectPrompt(card.query)}
          >
            <div className="video1-card-icon-badge">
              {card.icon}
            </div>
            <span className="video1-card-title">{card.title}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
