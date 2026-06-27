import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { analyzeProfile } from "../services/api";
import { STORAGE_KEY, SEVEN_DAYS_MS, getStoredSession, storeSession } from "../utils/session";

function normalize(url) {
  return url.trim().replace(/\/$/, "");
}

function Home() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const session = JSON.parse(raw);
      if (Date.now() - session.timestamp > SEVEN_DAYS_MS) {
        localStorage.removeItem(STORAGE_KEY);
        return;
      }
      navigate(`/dashboard/${session.session_id}`, {
        state: session.profile ? { profile: session.profile } : {},
      });
    } catch (_e) {
      // ignore malformed storage
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!url.includes("linkedin.com/in/")) {
      setError("Please enter a valid LinkedIn profile URL");
      return;
    }

    const cleanUrl = normalize(url);
    const stored = getStoredSession(cleanUrl);

    if (stored) {
      navigate(`/dashboard/${stored.session_id}`, {
        state: stored.profile ? { profile: stored.profile } : {},
      });
      return;
    }

    setLoading(true);
    try {
      const data = await analyzeProfile(cleanUrl);
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
