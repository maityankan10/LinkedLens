const SECTIONS = [
  { key: "strengths",             title: "Strengths",             icon: "✦", cls: "card--green"  },
  { key: "areas_for_improvement", title: "Areas for Improvement", icon: "◈", cls: "card--amber"  },
  { key: "content_ideas",         title: "Content Ideas",         icon: "◆", cls: "card--blue"   },
  { key: "recommended_topics",    title: "Recommended Topics",    icon: "▲", cls: "card--purple" },
];

function InsightsPanel({ insights }) {
  if (!insights) return null;

  return (
    <div className="insights-grid">
      {SECTIONS.map(({ key, title, icon, cls }) => {
        const items = insights[key] ?? [];
        return (
          <div key={key} className={`insight-card ${cls}`}>
            <div className="insight-card-header">
              <span className="insight-icon">{icon}</span>
              <h3 className="insight-title">{title}</h3>
            </div>
            <ul className="insight-list">
              {items.map((item, i) => (
                <li key={i} className="insight-item">{item}</li>
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}

export default InsightsPanel;
