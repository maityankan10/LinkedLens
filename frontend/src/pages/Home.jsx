import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { analyzeProfile } from "../services/api";

const STORAGE_KEY = "linkedlens_session";
const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000;

function normalize(url) {
  return url.trim().replace(/\/$/, "");
}

function getStoredSession(url) {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const session = JSON.parse(raw);
    if (session.linkedin_url !== url) return null;
    if (Date.now() - session.timestamp > SEVEN_DAYS_MS) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return session;
  } catch {
    return null;
  }
}

export function storeSession(url, sessionId, profile = null) {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({ linkedin_url: url, session_id: sessionId, timestamp: Date.now(), profile })
  );
}

function Home() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!url.includes("linkedin.com/in/")) {
      setError("Please enter a valid LinkedIn profile URL");
      return;
    }

    const cleanUrl = normalize(url);
    const stored = getStoredSession(cleanUrl);

    // Existing session — navigate with whatever we have (profile may be null if was pending)
    if (stored) {
      navigate(`/dashboard/${stored.session_id}`, {
        state: stored.profile ? { profile: stored.profile } : {},
      });
      return;
    }

    setLoading(true);
    try {
      const data = await analyzeProfile(cleanUrl);
      // Save session_id immediately; profile is null if still pending
      storeSession(cleanUrl, data.session_id, data.status === "ready" ? data : null);
      navigate(`/dashboard/${data.session_id}`, {
        state: data.status === "ready" ? { profile: data } : {},
      });
    } catch (err) {
      setError("Failed to analyze profile. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="home-container">
      <div className="home-card">
        <h1 className="home-title">LinkedLens</h1>
        <p className="home-subtitle">
          AI-powered LinkedIn profile analysis and coaching
        </p>

        <form onSubmit={handleSubmit} className="home-form">
          <input
            type="text"
            className="home-input"
            placeholder="https://www.linkedin.com/in/yourprofile"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="home-button" disabled={loading}>
            {loading ? "Starting analysis..." : "Analyze Profile"}
          </button>
        </form>

        {error && <p className="home-error">{error}</p>}
      </div>
    </div>
  );
}

export default Home;
