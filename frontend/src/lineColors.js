export const LINE_COLORS = {
  "1호선": "#3B82C4",
  "2호선": "#00A84D",
  "3호선": "#EF7C1C",
  "4호선": "#00A5DE",
  "5호선": "#996CAC",
  "6호선": "#CD7C2F",
  "7호선": "#9AA300",
  "8호선": "#E6186C",
  "9호선": "#D4B106",
  신분당선: "#D4003B",
}
export const LINE_ORDER = Object.keys(LINE_COLORS)

const FALLBACK_COLOR = "#8e8e93"

export function getLineColor(line) {
  return LINE_COLORS[line] || FALLBACK_COLOR
}

export function getLineLabel(line) {
  const match = line.match(/^(\d+)호선$/)
  return match ? match[1] : line[0]
}

export function getStationColor(node) {
  if (!node?.lines?.length) return FALLBACK_COLOR
  const colors = node.lines.map(getLineColor)
  if (colors.length === 1) return colors[0]
  return `linear-gradient(135deg, ${colors.join(", ")})`
}

export function getStationSolidColor(node) {
  if (!node?.lines?.length) return FALLBACK_COLOR
  return getLineColor(node.lines[0])
}
