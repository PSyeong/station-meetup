import { useState } from "react";
import { ChevronDown, ChevronLeft, RotateCcw } from "lucide-react";
import ResultMap from "../components/ResultMap.jsx";
import ModeToggle from "../components/ModeToggle.jsx";
import Spinner from "../../../components/Spinner.jsx";
import { getLineColor, getLineLabel, getStationColor } from "../../../lineColors.js";

function directionsUrl(node) {
  if (!node) return "#";
  return `https://map.kakao.com/link/to/${encodeURIComponent(node.name)},${node.lat},${node.lng}`;
}

export default function MapResultScene({
  graph,
  recommendations,
  selectedIndex,
  onSelectStation,
  onBack,
  onShowPlaces,
  mode,
  onChangeMode,
  changingMode,
  modeChangeError,
}) {
  const [showAlternatives, setShowAlternatives] = useState(false);
  const selected = recommendations[selectedIndex];
  const destNode = graph.nodes.find((n) => n.id === selected.station);
  const nodesById = new Map(graph.nodes.map((n) => [n.id, n]));
  const alternatives = recommendations
    .map((rec, index) => ({ rec, index }))
    .filter(({ index }) => index !== selectedIndex);

  return (
    <div className="scene scene--map">
      <header className="scene__header">
        <button type="button" className="scene__back" onClick={onBack} aria-label="뒤로가기">
          <ChevronLeft size={22} strokeWidth={2} />
        </button>
        <h2 className="scene__title">중간장소 결과 보기</h2>
        <span className="scene__header-spacer" aria-hidden="true" />
      </header>

      <div className="scene__map-area">
        <ResultMap
          graph={graph}
          recommendations={recommendations}
          selectedIndex={selectedIndex}
          onSelectStation={onSelectStation}
        />
      </div>

      <div className="map-sheet">
        <div className="map-sheet__mode">
          <div className="map-sheet__mode-label">
            검색 방식
            {changingMode && <Spinner size={12} />}
          </div>
          <ModeToggle mode={mode} onChange={onChangeMode} disabled={changingMode} />
          {modeChangeError && <p className="meeting-recommend__error">{modeChangeError}</p>}
        </div>

        <div className="map-sheet__station">
          {selected.station}
          <span className="map-sheet__station-lines">
            {destNode?.lines.map((line) => (
              <span key={line} className="line-badge" style={{ background: getLineColor(line) }}>
                {getLineLabel(line)}
              </span>
            ))}
          </span>
        </div>
        <div className="map-sheet__mean">평균 이동시간 {selected.mean_time}분</div>
        <div className="map-sheet__chips">
          {selected.travel_times.map((t) => (
            <span
              key={t.origin}
              className="map-sheet__chip"
              style={{ "--chip-color": getStationColor(nodesById.get(t.origin)) }}
            >
              <span className="map-sheet__chip-dot" />
              {t.origin} {t.time}분
            </span>
          ))}
        </div>

        {alternatives.length > 0 && (
          <div className="map-sheet__alternatives">
            <button
              type="button"
              className="map-sheet__alternatives-toggle"
              onClick={() => setShowAlternatives((v) => !v)}
              aria-expanded={showAlternatives}
            >
              다른 후보 {alternatives.length}곳 보기
              <ChevronDown
                size={16}
                strokeWidth={2}
                className={"map-sheet__alternatives-chevron" + (showAlternatives ? " map-sheet__alternatives-chevron--open" : "")}
              />
            </button>
            {showAlternatives && (
              <div className="map-sheet__alternatives-list">
                {alternatives.map(({ rec, index }) => (
                  <button
                    key={rec.station}
                    type="button"
                    className="map-sheet__alternative"
                    onClick={() => {
                      onSelectStation(index);
                      setShowAlternatives(false);
                    }}
                  >
                    <span className="map-sheet__alternative-rank">{index + 1}</span>
                    <span className="map-sheet__alternative-name">{rec.station}</span>
                    <span className="map-sheet__alternative-time">평균 {rec.mean_time}분</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        <button type="button" className="map-sheet__primary" onClick={onShowPlaces}>
          ⭐ 여기에서 뭐하지?
        </button>
        <div className="map-sheet__utility">
          <a className="map-sheet__util-link" href={directionsUrl(destNode)} target="_blank" rel="noreferrer">
            길찾기
          </a>
          <button type="button" className="map-sheet__util-link" onClick={onBack}>
            <RotateCcw size={14} strokeWidth={2} />
            다시하기
          </button>
        </div>
      </div>
    </div>
  );
}
