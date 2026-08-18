import { useEffect, useMemo, useRef, useState } from "react";

export default function StationAutocomplete({ value, onChange, graph, placeholder, invalid }) {
  const [open, setOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const containerRef = useRef(null);
  const optionRefs = useRef([]);

  const hits = useMemo(() => {
    if (!graph || !value.trim()) return [];
    return graph.nodes.filter((n) => n.name.includes(value.trim())).slice(0, 8);
  }, [graph, value]);

  useEffect(() => {
    setHighlightedIndex(hits.length > 0 ? 0 : -1);
  }, [hits]);

  useEffect(() => {
    if (highlightedIndex < 0) return;
    optionRefs.current[highlightedIndex]?.scrollIntoView({ block: "nearest" });
  }, [highlightedIndex]);

  useEffect(() => {
    if (!open) return;
    function handlePointerDown(ev) {
      if (!containerRef.current?.contains(ev.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [open]);

  function selectHit(n) {
    onChange(n.name);
    setOpen(false);
  }

  function handleKeyDown(ev) {
    if (!open || hits.length === 0) return;

    if (ev.key === "ArrowDown") {
      ev.preventDefault();
      setHighlightedIndex((i) => (i + 1) % hits.length);
    } else if (ev.key === "ArrowUp") {
      ev.preventDefault();
      setHighlightedIndex((i) => (i - 1 + hits.length) % hits.length);
    } else if (ev.key === "Enter") {
      if (ev.nativeEvent.isComposing) return;
      if (highlightedIndex >= 0 && highlightedIndex < hits.length) {
        ev.preventDefault();
        selectHit(hits[highlightedIndex]);
      }
    } else if (ev.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div className="station-autocomplete" ref={containerRef}>
      <input
        className={
          "station-autocomplete__input" + (invalid ? " station-autocomplete__input--invalid" : "")
        }
        type="text"
        role="combobox"
        aria-expanded={open && hits.length > 0}
        aria-autocomplete="list"
        aria-activedescendant={
          highlightedIndex >= 0 ? `station-option-${hits[highlightedIndex]?.id}` : undefined
        }
        value={value}
        placeholder={placeholder}
        onChange={(ev) => {
          onChange(ev.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
      />
      {open && hits.length > 0 && (
        <ul className="station-autocomplete__list" role="listbox">
          {hits.map((n, i) => (
            <li key={n.id}>
              <button
                id={`station-option-${n.id}`}
                ref={(el) => (optionRefs.current[i] = el)}
                type="button"
                role="option"
                aria-selected={i === highlightedIndex}
                className={
                  "station-autocomplete__option" +
                  (i === highlightedIndex ? " station-autocomplete__option--highlighted" : "")
                }
                onMouseEnter={() => setHighlightedIndex(i)}
                onClick={() => selectHit(n)}
              >
                <span>{n.name}</span>
                <span className="station-autocomplete__option-lines">{n.lines.join(" · ")}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {invalid && <p className="station-autocomplete__hint">목록에 있는 역명을 선택해주세요.</p>}
    </div>
  );
}
