export default function WelcomeHero({ onSelectPrompt }) {
  const starterPrompts = [
    {
      title: "Tomorrow's Forecast",
      desc: "Detailed conditions, precipitation, and thermal trends",
      query: "What's the weather in Dehradun tomorrow?",
      icon: "🌤️",
    },
    {
      title: "Umbrella & Rain Check",
      desc: "Evidence-based decision support for precipitation",
      query: "Should I carry an umbrella tomorrow in Dehradun?",
      icon: "☔",
    },
    {
      title: "Outdoor Activity Window",
      desc: "Find the best 6-hour block for outdoor sports or walking",
      query: "What is the best time for outdoor activities in Tokyo tomorrow?",
      icon: "🏃",
    },
    {
      title: "Temperature Trends",
      desc: "Analyze diurnal trajectory, morning warming and drops",
      query: "Is the temperature in Paris increasing or decreasing over the next 24 hours?",
      icon: "📈",
    },
  ];

  return (
    <div className="welcome-hero-container">
      <div className="welcome-hero-badge">🌦️ AI Weather Intelligence</div>
      <h2 className="welcome-hero-title">How can I help with the weather today?</h2>
      <p className="welcome-hero-subtitle">
        Ask natural-language questions. I inspect live Open-Meteo observations, analyze meteorological trends, and audit every claim with formal evidence proofs.
      </p>

      <div className="starter-prompts-grid">
        {starterPrompts.map((p, idx) => (
          <button
            key={idx}
            type="button"
            className="starter-prompt-card"
            onClick={() => onSelectPrompt(p.query)}
          >
            <span className="starter-icon">{p.icon}</span>
            <div className="starter-text">
              <strong className="starter-title">{p.title}</strong>
              <span className="starter-desc">{p.desc}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
