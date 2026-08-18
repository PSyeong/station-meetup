import { useEffect, useMemo, useRef, useState } from "react";
import "./ResultMap.css";
import { getKakaoJsKey, loadKakaoMaps } from "../kakaoMapLoader.js";
import { getLineColor, getStationColor, getStationSolidColor } from "../../../lineColors.js";
import Spinner from "../../../components/Spinner.jsx";
import { findShortestPath } from "../shortestPath.js";

function originPinHtml(label, color, name) {
  return `
    <div class="result-map__origin-pin">
      <span class="result-map__origin-pin-badge" style="background:${color}">${label}</span>
      <span class="result-map__origin-pin-label">${name}</span>
    </div>
  `;
}

function timeLabelHtml(text, color) {
  return `<div class="result-map__time-label" style="border-color:${color}">${text}</div>`;
}

export default function ResultMap({ graph, recommendations, selectedIndex, onSelectStation }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const overlaysRef = useRef([]);
  const [status, setStatus] = useState(getKakaoJsKey() ? "loading" : "missing-key");

  const nodesById = useMemo(() => new Map(graph.nodes.map((n) => [n.id, n])), [graph]);

  useEffect(() => {
    if (status === "missing-key" || mapRef.current) return;
    let cancelled = false;
    loadKakaoMaps()
      .then((kakao) => {
        if (cancelled || !containerRef.current || mapRef.current) return;
        mapRef.current = new kakao.maps.Map(containerRef.current, {
          center: new kakao.maps.LatLng(37.5665, 126.978),
          level: 6,
        });
        setStatus("ready");
      })
      .catch((err) => {
        console.error(err);
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (status !== "ready" || !mapRef.current || !window.kakao) return;
    const kakao = window.kakao;
    const map = mapRef.current;

    overlaysRef.current.forEach((overlay) => overlay.setMap(null));
    overlaysRef.current = [];

    const bounds = new kakao.maps.LatLngBounds();
    const selected = recommendations[selectedIndex];

    selected.travel_times.forEach((t, i) => {
      const node = nodesById.get(t.origin);
      if (!node) return;
      const pos = new kakao.maps.LatLng(node.lat, node.lng);
      bounds.extend(pos);
      const overlay = new kakao.maps.CustomOverlay({
        position: pos,
        yAnchor: 1.1,
        content: originPinHtml(String(i + 1), getStationColor(node), node.name),
      });
      overlay.setMap(map);
      overlaysRef.current.push(overlay);
    });

    recommendations.forEach((rec, idx) => {
      const node = nodesById.get(rec.station);
      if (!node) return;
      const pos = new kakao.maps.LatLng(node.lat, node.lng);
      bounds.extend(pos);
      const isSelected = idx === selectedIndex;

      const el = document.createElement("div");
      el.className = "result-map__dest-pin" + (isSelected ? " result-map__dest-pin--selected" : "");
      el.innerHTML = `<span class="result-map__dest-pin-badge">${idx + 1}</span><span class="result-map__dest-pin-label">${node.name}</span>`;
      el.addEventListener("click", () => onSelectStation(idx));

      const overlay = new kakao.maps.CustomOverlay({
        position: pos,
        yAnchor: 1,
        content: el,
        zIndex: isSelected ? 10 : 5,
      });
      overlay.setMap(map);
      overlaysRef.current.push(overlay);
    });

    const destNode = nodesById.get(selected.station);
    if (destNode) {
      const destPos = new kakao.maps.LatLng(destNode.lat, destNode.lng);
      selected.travel_times.forEach((t) => {
        const originNode = nodesById.get(t.origin);
        if (!originNode) return;
        const fallbackColor = getStationSolidColor(originNode);
        const routed = findShortestPath(graph, t.origin, selected.station);

        if (routed && routed.segments.length > 0) {
          let runStart = 0;
          for (let i = 0; i <= routed.segments.length; i++) {
            const isLastSegment = i === routed.segments.length;
            const lineChanged = !isLastSegment && routed.segments[i].line !== routed.segments[runStart].line;
            if (isLastSegment || lineChanged) {
              const runNodeIds = routed.path.slice(runStart, i + 1);
              const runPath = runNodeIds.map((id) => nodesById.get(id)).filter(Boolean);
              if (runPath.length >= 2) {
                const line = new kakao.maps.Polyline({
                  path: runPath.map((n) => new kakao.maps.LatLng(n.lat, n.lng)),
                  strokeWeight: 4,
                  strokeColor: getLineColor(routed.segments[runStart].line),
                  strokeOpacity: 0.85,
                  strokeStyle: "solid",
                });
                line.setMap(map);
                overlaysRef.current.push(line);
              }
              runStart = i;
            }
          }
        } else {
          const originPos = new kakao.maps.LatLng(originNode.lat, originNode.lng);
          const line = new kakao.maps.Polyline({
            path: [originPos, destPos],
            strokeWeight: 4,
            strokeColor: fallbackColor,
            strokeOpacity: 0.85,
            strokeStyle: "solid",
          });
          line.setMap(map);
          overlaysRef.current.push(line);
        }

        const midLat = (originNode.lat + destNode.lat) / 2;
        const midLng = (originNode.lng + destNode.lng) / 2;
        const label = new kakao.maps.CustomOverlay({
          position: new kakao.maps.LatLng(midLat, midLng),
          content: timeLabelHtml(`${t.origin}에서 ${t.time}분`, fallbackColor),
        });
        label.setMap(map);
        overlaysRef.current.push(label);
      });
    }

    map.setBounds(bounds, 60, 60, 60, 60);
  }, [status, recommendations, selectedIndex, nodesById, onSelectStation]);

  if (status === "missing-key") {
    return (
      <div className="result-map__fallback">
        <p>
          <strong>카카오맵 JS 키가 설정되지 않았습니다.</strong>
        </p>
        <p>frontend/.env에 VITE_KAKAO_JS_KEY를 설정하면 지도가 표시됩니다.</p>
      </div>
    );
  }
  if (status === "error") {
    return (
      <div className="result-map__fallback">
        <p>
          <strong>카카오맵을 불러오지 못했습니다.</strong>
        </p>
        <p>키 값과 카카오 개발자 콘솔에 등록된 도메인(localhost 포함)을 확인해주세요.</p>
      </div>
    );
  }

  return (
    <>
      <div ref={containerRef} className="result-map" />
      {status === "loading" && (
        <div className="result-map__loading">
          <Spinner />
        </div>
      )}
    </>
  );
}
