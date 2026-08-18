const MODES = [
  { id: "fair", label: "공평하게", desc: "이동시간 차이 최소화" },
  { id: "fast", label: "빠르게", desc: "평균 이동시간 최소화" },
  { id: "balanced", label: "균형 있게", desc: "효율과 형평성 함께 고려" },
];

export default function ModeToggle({ mode, onChange }) {
  return (
    <div className="mode-toggle" role="radiogroup" aria-label="추천 모드">
      {MODES.map((m) => (
        <button
          key={m.id}
          type="button"
          role="radio"
          aria-checked={mode === m.id}
          className={"mode-toggle__btn" + (mode === m.id ? " mode-toggle__btn--active" : "")}
          onClick={() => onChange(m.id)}
        >
          <span className="mode-toggle__label">{m.label}</span>
          <span className="mode-toggle__desc">{m.desc}</span>
        </button>
      ))}
    </div>
  );
}
