async function requestJson(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const payload = await res.json().catch(() => null);
    throw new Error(payload?.detail || `요청에 실패했습니다 (HTTP ${res.status})`);
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
