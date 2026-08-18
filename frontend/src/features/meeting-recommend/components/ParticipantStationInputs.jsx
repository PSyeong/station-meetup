import StationAutocomplete from "./StationAutocomplete.jsx";
import { generateId } from "../../../generateId.js";

export const MIN_PARTICIPANTS = 2;
export const MAX_PARTICIPANTS = 5;

function makeParticipant() {
  return { id: generateId(), stationName: "" };
}

export default function ParticipantStationInputs({ participants, onChange, graph, invalidIds }) {
  function updateStation(id, stationName) {
    onChange(participants.map((p) => (p.id === id ? { ...p, stationName } : p)));
  }
  function addParticipant() {
    if (participants.length >= MAX_PARTICIPANTS) return;
    onChange([...participants, makeParticipant()]);
  }
  function removeParticipant(id) {
    if (participants.length <= MIN_PARTICIPANTS) return;
    onChange(participants.filter((p) => p.id !== id));
  }
  function resetParticipants() {
    onChange([makeParticipant(), makeParticipant()]);
  }

  return (
    <div className="participant-inputs">
      {participants.map((p, i) => (
        <div key={p.id} className="participant-inputs__row">
          <span className="participant-inputs__index">{i + 1}</span>
          <StationAutocomplete
            value={p.stationName}
            onChange={(v) => updateStation(p.id, v)}
            graph={graph}
            placeholder="출발역을 입력해주세요"
            invalid={invalidIds?.includes(p.id)}
          />
          {participants.length > MIN_PARTICIPANTS && (
            <button
              type="button"
              className="participant-inputs__remove"
              onClick={() => removeParticipant(p.id)}
              aria-label="참여자 삭제"
            >
              ✕
            </button>
          )}
        </div>
      ))}
      <div className="participant-inputs__actions">
        <button type="button" className="participant-inputs__reset" onClick={resetParticipants}>
          초기화
        </button>
        <button
          type="button"
          className="participant-inputs__add"
          onClick={addParticipant}
          disabled={participants.length >= MAX_PARTICIPANTS}
        >
          + 참여자 추가 ({participants.length}/{MAX_PARTICIPANTS})
        </button>
      </div>
    </div>
  );
}
