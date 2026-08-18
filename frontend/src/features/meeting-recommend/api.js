import { trackEvent } from "../../analytics.js";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

async function requestJson(path, body) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err) {
    trackEvent("api_error", { path, message: err.message });
    throw err;
  }
  if (!res.ok) {
    const payload = await res.json().catch(() => null);
    const message = payload?.detail || `요청에 실패했습니다 (HTTP ${res.status})`;
    trackEvent("api_error", { path, status: res.status, message });
    throw new Error(message);
  }
  return res.json();
}

export function fetchRecommendations({ origins, mode, topK = 3 }) {
  return requestJson("/api/recommendations", { origins, mode, top_k: topK });
}

export async function fetchPlaces({ stationId }) {
  const result = await requestJson("/api/places", { station_id: stationId });
  return result.places;
}
