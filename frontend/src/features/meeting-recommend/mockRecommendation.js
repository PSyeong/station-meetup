const AVG_SPEED_KMH = 33
const TRANSFER_OVERHEAD_MIN = 4.5

export const RECOMMENDATION_MODES = {
  fair: { w_mean: 0.2, w_max: 0.3, w_gap: 0.5 },
  fast: { w_mean: 0.7, w_max: 0.2, w_gap: 0.1 },
  balanced: { w_mean: 0.5, w_max: 0.3, w_gap: 0.2 },
}
export const DEFAULT_MODE = "fair"

function toRad(deg) {
  return (deg * Math.PI) / 180
}

function haversineKm(a, b) {
  const R = 6371
  const dLat = toRad(b.lat - a.lat)
  const dLng = toRad(b.lng - a.lng)
  const lat1 = toRad(a.lat)
  const lat2 = toRad(b.lat)
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(h))
}

function estimateMinutes(a, b) {
  const distanceKm = haversineKm(a, b)
  return Math.round((distanceKm / AVG_SPEED_KMH) * 60 + TRANSFER_OVERHEAD_MIN)
}

function round2(n) {
  return Math.round(n * 100) / 100
}

export function generateMockRecommendations({
  graph,
  origins,
  mode = DEFAULT_MODE,
  topK = 3,
}) {
  if (!graph) throw new Error("station graph가 필요합니다.")
  if (!origins || origins.length === 0)
    throw new Error("origins는 최소 1명 이상이어야 합니다.")

  const weights =
    RECOMMENDATION_MODES[mode] ?? RECOMMENDATION_MODES[DEFAULT_MODE]
  const nodesById = new Map(graph.nodes.map((n) => [n.id, n]))
  const originNodes = origins.map((id) => nodesById.get(id))
  const missing = origins.filter((_, i) => !originNodes[i])
  if (missing.length > 0)
    throw new Error(`알 수 없는 출발역: ${missing.join(", ")}`)

  const evaluated = graph.nodes.map((candidate) => {
    const travel_times = origins.map((origin, i) => ({
      origin,
      time: estimateMinutes(originNodes[i], candidate),
    }))
    const times = travel_times.map((t) => t.time)
    const mean_time = round2(times.reduce((a, b) => a + b, 0) / times.length)
    const max_time = Math.max(...times)
    const min_time = Math.min(...times)
    const time_gap = max_time - min_time
    const variance =
      times.reduce((a, t) => a + (t - mean_time) ** 2, 0) / times.length
    const std_time = round2(Math.sqrt(variance))
    const score = round2(
      weights.w_mean * mean_time +
        weights.w_max * max_time +
        weights.w_gap * time_gap
    )
    const longest_travel = travel_times.reduce((a, b) =>
      b.time > a.time ? b : a
    )
    const shortest_travel = travel_times.reduce((a, b) =>
      b.time < a.time ? b : a
    )

    return {
      station: candidate.id,
      score,
      mean_time,
      max_time,
      min_time,
      time_gap,
      std_time,
      travel_times,
      longest_travel,
      shortest_travel,
    }
  })

  evaluated.sort((a, b) => a.score - b.score)
  return evaluated.slice(0, Math.min(topK, evaluated.length))
}
