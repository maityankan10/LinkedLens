export const STORAGE_KEY = "linkedlens_session";
export const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000;

export function getStoredSession(url) {
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
  } catch (_e) {
    return null;
  }
}

export function storeSession(url, sessionId, profile = null) {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({ linkedin_url: url, session_id: sessionId, timestamp: Date.now(), profile })
  );
}

export function clearSession() {
  localStorage.removeItem(STORAGE_KEY);
}
