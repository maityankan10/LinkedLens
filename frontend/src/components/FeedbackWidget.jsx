import { useState } from "react";
import { submitFeedback } from "../services/api";

function FeedbackWidget({ sessionId }) {
  const [vote, setVote] = useState(null);
  const [text, setText] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleVote = (v) => {
    if (submitted) return;
    setVote(v);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await submitFeedback(sessionId, vote === "up", text.trim() || null);
      setSubmitted(true);
    } catch (_e) {
      // still mark submitted so UI doesn't get stuck
      setSubmitted(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="feedback">
      {submitted ? (
        <p className="feedback-thanks">Thanks for your feedback!</p>
      ) : (
        <>
          <div className="feedback-row">
            <span className="feedback-label">Was this analysis helpful?</span>
            <button
              className={`feedback-btn ${vote === "up" ? "feedback-btn--active-up" : ""}`}
              onClick={() => handleVote("up")}
              title="Yes"
            >
              👍
            </button>
            <button
              className={`feedback-btn ${vote === "down" ? "feedback-btn--active-down" : ""}`}
              onClick={() => handleVote("down")}
              title="No"
            >
              👎
            </button>
          </div>

          {vote && (
            <form className="feedback-form" onSubmit={handleSubmit}>
              <input
                className="feedback-input"
                type="text"
                placeholder="Tell us more (optional)"
                value={text}
                onChange={(e) => setText(e.target.value)}
                disabled={loading}
              />
              <button className="feedback-submit" type="submit" disabled={loading}>
                {loading ? "Saving..." : "Submit"}
              </button>
            </form>
          )}
        </>
      )}
    </div>
  );
}

export default FeedbackWidget;
