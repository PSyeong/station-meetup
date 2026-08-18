import { useMemo, useState } from "react";
import ParticipantStationInputs, { MIN_PARTICIPANTS } from "../components/ParticipantStationInputs.jsx";
import ModeToggle from "../components/ModeToggle.jsx";
import Spinner from "../../../components/Spinner.jsx";

const DEFAULT_MODE = "fair";

function makeParticipant() {
  return { id: crypto.randomUUID(), stationName: "" };
}

export default function InputScene({ graph, onSubmit, submitting, submitError }) {
  const [participants, setParticipants] = useState(() => [makeParticipant(), makeParticipant()]);
  const [mode, setMode] = useState(DEFAULT_MODE);
  const [formError, setFormError] = useState(null);

  const stationNameSet = useMemo(() => new Set(graph.nodes.map((n) => n.name)), [graph]);

  const invalidIds = useMemo(
    () =>
      participants
        .filter((p) => p.stationName.trim() && !stationNameSet.has(p.stationName.trim()))
        .map((p) => p.id),
    [participants, stationNameSet]
  );

  const canSubmit =
    !submitting &&
    participants.length >= MIN_PARTICIPANTS &&
    participants.every((p) => p.stationName.trim() && stationNameSet.has(p.stationName.trim()));

  function handleSubmit(ev) {
    ev.preventDefault();
    if (!canSubmit) return;
    const origins = participants.map((p) => p.stationName.trim());
    if (new Set(origins).size !== origins.length) {
      setFormError("같은 역을 중복해서 입력할 수 없습니다.");
      return;
    }
    setFormError(null);
    onSubmit(origins, mode);
  }

  return (
    <div className="input-scene">
      <div className="input-scene__card">
        <div className="input-scene__mark" aria-hidden="true">
          🚇
        </div>
        <h1 className="input-scene__headline">
          출발역을 입력하고
          <br />
          중간장소를 찾아보세요!
        </h1>

        <form onSubmit={handleSubmit}>
          <ParticipantStationInputs
            participants={participants}
            onChange={setParticipants}
            graph={graph}
            invalidIds={invalidIds}
          />

          <div className="input-scene__mode">
            <div className="input-scene__mode-label">검색 방식</div>
            <ModeToggle mode={mode} onChange={setMode} />
          </div>

          {formError && <p className="meeting-recommend__error">{formError}</p>}
          {submitError && <p className="meeting-recommend__error">{submitError}</p>}

          <button type="submit" className="input-scene__submit" disabled={!canSubmit}>
            {submitting ? <Spinner size={14} light /> : "중간장소 찾기"}
          </button>
        </form>
      </div>
    </div>
  );
}
