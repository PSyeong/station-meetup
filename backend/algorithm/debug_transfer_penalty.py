"""
find_shortest_path()가 실제로 어떤 edge들의 합으로 최단 소요시간을 만드는지
edge 단위로 뜯어보는 디버그/분석 스크립트.

목적: station_graph.json에 이미 구워진(baked-in) 환승 페널티가 "실제 노선
변경" 여부와 무관하게 붙고 있다는 가설을, 실제 최단경로 결과로 검증한다.

주의:
- station_graph.json, backend/algorithm/shortest_path.py 모두 수정하지 않는다.
- find_shortest_path()를 그대로 호출해서 나온 경로만 사후 분석한다.
- pytest 대상이 아닌 독립 실행 스크립트다.

실행:
    python backend/algorithm/debug_transfer_penalty.py [출발역] [도착역]
    (인자 없으면 기본값 혜화 -> 강남)
"""

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.algorithm.shortest_path import find_shortest_path  # noqa: E402

GRAPH_PATH = ROOT_DIR / "data" / "station_graph.json"
TRANSFER_PENALTY_MIN = 4.5  # data/scripts/build_graph.py의 값과 동일


def load_graph():
    with open(GRAPH_PATH, encoding="utf-8") as f:
        data = json.load(f)
    nodes_by_id = {n["id"]: n for n in data["nodes"]}
    edge_lookup = {(e["from"], e["to"]): e for e in data["edges"]}
    return nodes_by_id, edge_lookup


def analyze(start: str, end: str) -> None:
    nodes_by_id, edge_lookup = load_graph()

    result = find_shortest_path(start, end)
    path = result["path"]

    print(f"find_shortest_path({start!r}, {end!r})")
    print(f"  -> total_time_min: {result['total_time_min']}")
    print(f"  -> path: {' -> '.join(path)}")
    print()
    print("=" * 60)
    print()

    stored_total = 0.0
    base_total = 0.0
    penalty_edge_count = 0
    actual_transfers = []  # (station, from_line, to_line)
    prev_line = None

    for a, b in zip(path, path[1:]):
        edge = edge_lookup[(a, b)]
        line = edge["line"]
        stored_time = edge["time_min"]

        from_transfer = nodes_by_id[a]["is_transfer"]
        to_transfer = nodes_by_id[b]["is_transfer"]
        # build_graph.py의 조건과 동일: na["is_transfer"] or nb["is_transfer"]
        penalty_baked_in = from_transfer or to_transfer
        base_time = round(stored_time - TRANSFER_PENALTY_MIN, 2) if penalty_baked_in else stored_time

        line_changed = prev_line is not None and line != prev_line

        print(f"{a} → {b}")
        print(f"  line: {line}")
        print(f"  stored time: {stored_time}")
        print(f"  either endpoint is_transfer: {'YES' if penalty_baked_in else 'NO'}  "
              f"({a}={from_transfer}, {b}={to_transfer})")
        print(f"  transfer penalty baked in: {'YES' if penalty_baked_in else 'NO'}")
        print(f"  base time (stored - {TRANSFER_PENALTY_MIN} if baked in): {base_time}")
        print(f"  previous line: {prev_line if prev_line is not None else '-'}")
        print(f"  actual line change: {'YES' if line_changed else 'NO'}"
              + ("  -> REAL TRANSFER at " + a if line_changed else ""))
        print()

        stored_total += stored_time
        base_total += base_time
        if penalty_baked_in:
            penalty_edge_count += 1
        if line_changed:
            actual_transfers.append((a, prev_line, line))

        prev_line = line

    baked_penalty_total = penalty_edge_count * TRANSFER_PENALTY_MIN
    corrected_total = base_total + len(actual_transfers) * TRANSFER_PENALTY_MIN

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"전체 경로: {' -> '.join(path)}")
    print(f"edge 개수: {len(path) - 1}")
    print()
    print(f"Stored total time: {round(stored_total, 2)} min")
    print(f"Base travel time: {round(base_total, 2)} min")
    print()
    print("Baked transfer penalties (현재 방식 - 통과만 해도 적용):")
    print(f"{penalty_edge_count} edges x {TRANSFER_PENALTY_MIN} min = {round(baked_penalty_total, 2)} min")
    print()
    print("Actual transfers (line 필드가 실제로 바뀐 지점만):")
    print(f"{len(actual_transfers)} times")
    for station, from_line, to_line in actual_transfers:
        print(f"  {station}: {from_line} -> {to_line}")
    print()
    print("Corrected estimated time (실제 환승에만 페널티 적용 시):")
    print(f"{round(base_total, 2)} + ({len(actual_transfers)} x {TRANSFER_PENALTY_MIN}) "
          f"= {round(corrected_total, 2)} min")


if __name__ == "__main__":
    start = sys.argv[1] if len(sys.argv) > 1 else "혜화"
    end = sys.argv[2] if len(sys.argv) > 2 else "강남"
    analyze(start, end)