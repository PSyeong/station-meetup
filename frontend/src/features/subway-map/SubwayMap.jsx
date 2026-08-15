import { useEffect, useMemo, useRef, useState } from "react";
import "./SubwayMap.css";

const LINE_COLORS = {
  "1호선": "#3B82C4",
  "2호선": "#00A84D",
  "3호선": "#EF7C1C",
  "4호선": "#00A5DE",
  "5호선": "#996CAC",
  "6호선": "#CD7C2F",
  "7호선": "#9AA300",
  "8호선": "#E6186C",
  "9호선": "#D4B106",
  "신분당선": "#D4003B",
};
const LINE_ORDER = Object.keys(LINE_COLORS);

export default function SubwayMap() {
  const [graph, setGraph] = useState(null);
  const [error, setError] = useState(null);
  const [activeLines, setActiveLines] = useState(() =>
    Object.fromEntries(LINE_ORDER.map((l) => [l, true]))
  );
  const [viewBox, setViewBox] = useState({ x: 0, y: 0, w: 1000, h: 1000 });
  const [hovered, setHovered] = useState(null);
  const [query, setQuery] = useState("");

  const svgRef = useRef(null);
  const dragRef = useRef(null);

  useEffect(() => {
    fetch("/data/station_graph.json")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(setGraph)
      .catch((err) => setError(err.message));
  }, []);

  const { nodesById, projectedNodes, edges, lineCounts } = useMemo(() => {
    if (!graph) return { nodesById: {}, projectedNodes: [], edges: [], lineCounts: {} };

    const lats = graph.nodes.map((n) => n.lat);
    const lngs = graph.nodes.map((n) => n.lng);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);
    const PAD = 30;
    const W = 1000;
    const H = 1000;
    const latSpan = maxLat - minLat;
    const lngSpan = maxLng - minLng;
    const scale = Math.min((W - PAD * 2) / lngSpan, (H - PAD * 2) / latSpan);
    const offX = (W - lngSpan * scale) / 2;
    const offY = (H - latSpan * scale) / 2;

    const projectedNodes = graph.nodes.map((n) => ({
      ...n,
      x: (n.lng - minLng) * scale + offX,
      y: (maxLat - n.lat) * scale + offY,
    }));
    const nodesById = Object.fromEntries(projectedNodes.map((n) => [n.id, n]));

    // station_graph.json은 양방향 엣지를 모두 저장하므로 렌더링용으로 한 번씩만 사용
    const seen = new Set();
    const edges = [];
    for (const e of graph.edges) {
      const key = [e.from, e.to].sort().join("|") + "|" + e.line;
      if (seen.has(key)) continue;
      seen.add(key);
      edges.push(e);
    }

    const lineCounts = Object.fromEntries(LINE_ORDER.map((l) => [l, 0]));
    for (const n of graph.nodes) {
      for (const l of n.lines) {
        if (lineCounts[l] != null) lineCounts[l]++;
      }
    }

    return { nodesById, projectedNodes, edges, lineCounts };
  }, [graph]);

  const searchHits = useMemo(() => {
    if (!query.trim() || !graph) return [];
    return graph.nodes.filter((n) => n.name.includes(query)).slice(0, 12);
  }, [query, graph]);

  function toggleLine(line) {
    setActiveLines((prev) => ({ ...prev, [line]: !prev[line] }));
  }
  function setAllLines(value) {
    setActiveLines(Object.fromEntries(LINE_ORDER.map((l) => [l, value])));
  }

  function focusNode(node) {
    const size = 140;
    setViewBox({ x: node.x - size / 2, y: node.y - size / 2, w: size, h: size });
  }

  function zoomAt(factor, cx, cy) {
    setViewBox((vb) => {
      const newW = Math.max(60, Math.min(2200, vb.w * factor));
      const newH = Math.max(60, Math.min(2200, vb.h * factor));
      const fx = (cx - vb.x) / vb.w;
      const fy = (cy - vb.y) / vb.h;
      return { x: cx - fx * newW, y: cy - fy * newH, w: newW, h: newH };
    });
  }

  function handlePointerDown(ev) {
    dragRef.current = { startX: ev.clientX, startY: ev.clientY, vb: viewBox };
    ev.currentTarget.setPointerCapture(ev.pointerId);
  }
  function handlePointerMove(ev) {
    if (!dragRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const { startX, startY, vb } = dragRef.current;
    const dx = (ev.clientX - startX) * (vb.w / rect.width);
    const dy = (ev.clientY - startY) * (vb.h / rect.height);
    setViewBox({ ...vb, x: vb.x - dx, y: vb.y - dy });
  }
  function handlePointerUp() {
    dragRef.current = null;
  }
  function handleWheel(ev) {
    ev.preventDefault();
    const rect = svgRef.current.getBoundingClientRect();
    const px = viewBox.x + (ev.clientX - rect.left) * (viewBox.w / rect.width);
    const py = viewBox.y + (ev.clientY - rect.top) * (viewBox.h / rect.height);
    zoomAt(ev.deltaY > 0 ? 1.12 : 0.89, px, py);
  }

  if (error) {
    return (
      <div className="subway-map__status">
        <p>
          <strong>데이터를 불러오지 못했습니다.</strong>
        </p>
        <p>data/station_graph.json이 있는지, dev 서버(npm run dev)가 실행 중인지 확인해주세요.</p>
        <p className="subway-map__status-detail">{error}</p>
      </div>
    );
  }

  if (!graph) {
    return <div className="subway-map__status">불러오는 중...</div>;
  }

  return (
    <div className="subway-map">
      <aside className="subway-map__sidebar">
        <div>
          <div className="subway-map__section-label">역 검색</div>
          <input
            className="subway-map__search"
            type="text"
            placeholder="역 이름으로 찾기..."
            value={query}
            onChange={(ev) => setQuery(ev.target.value)}
          />
          <div className="subway-map__search-results">
            {searchHits.map((n) => (
              <button
                key={n.id}
                className="subway-map__search-hit"
                onClick={() => focusNode(nodesById[n.id])}
              >
                <span className="subway-map__dot" style={{ background: LINE_COLORS[n.lines[0]] || "#888" }} />
                {n.name}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="subway-map__section-label">노선</div>
          <div className="subway-map__btn-row">
            <button className="subway-map__mini-btn" onClick={() => setAllLines(true)}>
              전체 보기
            </button>
            <button className="subway-map__mini-btn" onClick={() => setAllLines(false)}>
              모두 끄기
            </button>
          </div>
          <div className="subway-map__line-list">
            {LINE_ORDER.map((line) => (
              <div
                key={line}
                className={
                  "subway-map__line-toggle" + (activeLines[line] ? "" : " subway-map__line-toggle--off")
                }
                onClick={() => toggleLine(line)}
              >
                <span className="subway-map__swatch" style={{ background: LINE_COLORS[line] }} />
                <span className="subway-map__line-name">{line}</span>
                <span className="subway-map__line-count">{lineCounts[line]}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="subway-map__legend-note">
          <strong>사용법</strong> — 캔버스를 드래그해 이동, 휠로 확대/축소. 노선 이름을 클릭하면 해당
          노선만 켜고 끌 수 있어요. 역에 마우스를 올리면 이름과 소속 노선이 뜹니다. 흰 테두리가 있는
          역이 환승역입니다.
        </div>
      </aside>

      <div className="subway-map__canvas-wrap">
        <div className="subway-map__stats">
          <span>
            역 <b>{graph.meta.station_count}</b>
          </span>
          <span>
            구간 <b>{edges.length}</b>
          </span>
          <span>
            환승역 <b>{graph.nodes.filter((n) => n.is_transfer).length}</b>
          </span>
        </div>

        <svg
          ref={svgRef}
          className="subway-map__svg"
          viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`}
          preserveAspectRatio="xMidYMid meet"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
          onWheel={handleWheel}
        >
          <g>
            {edges.map((e, i) => {
              const na = nodesById[e.from];
              const nb = nodesById[e.to];
              if (!na || !nb) return null;
              return (
                <line
                  key={i}
                  x1={na.x}
                  y1={na.y}
                  x2={nb.x}
                  y2={nb.y}
                  stroke={LINE_COLORS[e.line] || "#888"}
                  strokeWidth={1.6}
                  strokeLinecap="round"
                  style={{ display: activeLines[e.line] ? "" : "none" }}
                />
              );
            })}
          </g>
          <g>
            {projectedNodes.map((n) => {
              const visible = n.lines.some((l) => activeLines[l]);
              const color = LINE_COLORS[n.lines[0]] || "#888";
              return (
                <circle
                  key={n.id}
                  cx={n.x}
                  cy={n.y}
                  r={n.is_transfer ? 4.2 : 2.4}
                  fill={n.is_transfer ? "var(--bg-elevated)" : color}
                  stroke={color}
                  strokeWidth={n.is_transfer ? 1.8 : 0}
                  style={{ display: visible ? "" : "none", cursor: "pointer" }}
                  onMouseEnter={(ev) => {
                    const rect = svgRef.current.getBoundingClientRect();
                    setHovered({ node: n, x: ev.clientX - rect.left, y: ev.clientY - rect.top });
                  }}
                  onMouseMove={(ev) => {
                    const rect = svgRef.current.getBoundingClientRect();
                    setHovered((h) => (h ? { ...h, x: ev.clientX - rect.left, y: ev.clientY - rect.top } : h));
                  }}
                  onMouseLeave={() => setHovered(null)}
                />
              );
            })}
          </g>
        </svg>

        <div className="subway-map__zoom-controls">
          <button
            className="subway-map__zoom-btn"
            onClick={() => zoomAt(0.8, viewBox.x + viewBox.w / 2, viewBox.y + viewBox.h / 2)}
          >
            +
          </button>
          <button
            className="subway-map__zoom-btn"
            onClick={() => zoomAt(1.25, viewBox.x + viewBox.w / 2, viewBox.y + viewBox.h / 2)}
          >
            −
          </button>
          <button className="subway-map__zoom-btn" onClick={() => setViewBox({ x: 0, y: 0, w: 1000, h: 1000 })}>
            ⤢
          </button>
        </div>

        {hovered && (
          <div className="subway-map__tooltip" style={{ left: hovered.x, top: hovered.y }}>
            <div>
              <strong>{hovered.node.name}</strong>
            </div>
            <div className="subway-map__tooltip-lines">
              {hovered.node.lines.map((l) => (
                <span key={l} style={{ background: LINE_COLORS[l] || "#888" }} />
              ))}
            </div>
            <div className="subway-map__tooltip-sub">{hovered.node.lines.join(" · ")}</div>
          </div>
        )}
      </div>
    </div>
  );
}
