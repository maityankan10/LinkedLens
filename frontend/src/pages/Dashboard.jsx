import { useLocation, useParams, useNavigate } from "react-router-dom";
import { useEffect, useState, useRef } from "react";
import ProfileCard from "../components/ProfileCard";
import InsightsPanel from "../components/InsightsPanel";
import ChatWindow from "../components/ChatWindow";
import FeedbackWidget from "../components/FeedbackWidget";
import { getAnalysisStatus } from "../services/api";

const STORAGE_KEY = "linkedlens_session";
const POLL_INTERVAL_MS = 3000;

function updateStoredProfile(profile) {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const session = JSON.parse(raw);
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...session, profile }));
  } catch {}
}

function Dashboard() {
  const { sessionId } = useParams();
  const { state } = useLocation();
  const navigate = useNavigate();

  const [profile, setProfile] = useState(state?.profile ?? null);
  const [analysisError, setAnalysisError] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const pollRef = useRef(null);

  useEffect(() => {
    if (!sessionId) { navigate("/"); return; }
    if (profile) return; // already have data, no polling needed

    pollRef.current = setInterval(async () => {
      try {
        const data = await getAnalysisStatus(sessionId);
        if (data.status === "ready") {
          clearInterval(pollRef.current);
          updateStoredProfile(data);
          setProfile(data);
        } else if (data.status === "error") {
          clearInterval(pollRef.current);
          setAnalysisError(true);
        }
      } catch {
        // network hiccup — keep polling
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(pollRef.current);
  }, [sessionId, profile, navigate]);

  if (analysisError) {
    return (
      <div className="db">
        <header className="db-header">
          <div className="db-header-inner">
            <span className="db-logo">LinkedLens</span>
            <button className="db-back-btn" onClick={() => navigate("/")}>← New Analysis</button>
          </div>
        </header>
        <div className="db-error">
          <p>Analysis failed. Please try again.</p>
          <button className="home-button" onClick={() => navigate("/")}>Go Back</button>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="db">
        <header className="db-header">
          <div className="db-header-inner">
            <span className="db-logo">LinkedLens</span>
            <button className="db-back-btn" onClick={() => navigate("/")}>← Cancel</button>
          </div>
        </header>
        <div className="db-loading">
          <div className="db-spinner" />
          <p className="db-loading-title">Analyzing profile...</p>
          <p className="db-loading-sub">This may take a few minutes. You can close this tab and come back — we'll save your progress.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="db">
      <header className="db-header">
        <div className="db-header-inner">
          <span className="db-logo">LinkedLens</span>
          <button className="db-back-btn" onClick={() => navigate("/")}>
            ← New Analysis
          </button>
        </div>
      </header>

      <div className="db-page">
        <div className="db-main">
          <ProfileCard profile={profile} />
          <InsightsPanel insights={profile.insights} />
          <FeedbackWidget sessionId={sessionId} />
        </div>

        {chatOpen && (
          <div className="db-chat-panel">
            <ChatWindow sessionId={sessionId} onClose={() => setChatOpen(false)} />
          </div>
        )}
      </div>

      {!chatOpen && (
        <button className="chat-fab" onClick={() => setChatOpen(true)} title="Open AI Coach">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
          </svg>
        </button>
      )}
    </div>
  );
}

export default Dashboard;
