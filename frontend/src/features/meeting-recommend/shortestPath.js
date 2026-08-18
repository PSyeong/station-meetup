export function findShortestPath(graph, startId, endId) {
  if (startId === endId) return { path: [startId], segments: [] }

  const adjacency = new Map()
  for (const edge of graph.edges) {
    if (!adjacency.has(edge.from)) adjacency.set(edge.from, [])
    adjacency.get(edge.from).push(edge)
  }

  const dist = new Map([[startId, 0]])
  const prevEdge = new Map()
  const visited = new Set()

  while (true) {
    let current = null
    let currentDist = Infinity
    for (const [id, d] of dist) {
      if (!visited.has(id) && d < currentDist) {
        current = id
        currentDist = d
      }
    }
    if (current === null || current === endId) break
    visited.add(current)

    for (const edge of adjacency.get(current) || []) {
      const nd = currentDist + edge.time_min
      if (!dist.has(edge.to) || nd < dist.get(edge.to)) {
        dist.set(edge.to, nd)
        prevEdge.set(edge.to, edge)
      }
    }
  }

  if (!dist.has(endId)) return null

  const path = [endId]
  const segments = []
  let cur = endId
  while (cur !== startId) {
    const edge = prevEdge.get(cur)
    if (!edge) return null
    segments.push(edge)
    cur = edge.from
    path.push(cur)
  }
  path.reverse()
  segments.reverse()

  return { path, segments }
}
