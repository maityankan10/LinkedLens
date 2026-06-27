import axios from "axios";

const BASE_URL = "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

export const analyzeProfile = async (linkedinUrl) => {
  const response = await api.post("/linkedin/analyze", {
    linkedin_url: linkedinUrl,
  });
  return response.data;
};

export const sendChatMessage = async (sessionId, message) => {
  const response = await api.post("/linkedin/chat", {
    session_id: sessionId,
    message,
  });
  return response.data;
};

export const getAnalysisStatus = async (sessionId) => {
  const response = await api.get(`/linkedin/status/${sessionId}`);
  return response.data;
};

export const submitFeedback = async (sessionId, helpful, comment = null) => {
  const response = await api.post("/linkedin/feedback", {
    session_id: sessionId,
    helpful,
    comment,
  });
  return response.data;
};