"""backend/algorithm/shortest_path.py 검증 테스트.

실행: python -m pytest tests/test_shortest_path.py -v
(프로젝트에 pyproject.toml/setup.cfg가 없어 backend 패키지가 sys.path에
 잡히지 않으므로, 이 파일에서 프로젝트 루트를 sys.path에 직접 추가한다.)
"""

import json
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.algorithm.shortest_path import (  # noqa: E402
    NoPathFoundError,
    StationGraph,
    StationNotFoundError,
    find_shortest_path,
    get_shortest_times_from,
)

GRAPH_PATH = ROOT_DIR / "data" / "station_graph.json"
with open(GRAPH_PATH, encoding="utf-8") as f:
    _RAW_GRAPH = json.load(f)

_VALID_EDGES = {(e["from"], e["to"]) for e in _RAW_GRAPH["edges"]}
_LINES_BY_STATION = {n["id"]: n["lines"] for n in _RAW_GRAPH["nodes"]}
_IS_TRANSFER_BY_ID = {n["id"]: n["is_transfer"] for n in _RAW_GRAPH["nodes"]}
_RAW_EDGE_BY_PAIR = {(e["from"], e["to"]): e for e in _RAW_GRAPH["edges"]}
TRANSFER_PENALTY_MIN = 4.5


def assert_path_is_valid(result: dict, start: str, end: str) -> None:
    """path의 각 구간이 실제 edge로 연결돼 있는지 station_graph.json과 대조 검증."""
    assert result["start"] == start
    assert result["end"] == end
    assert result["path"][0] == start
    assert result["path"][-1] == end
    for a, b in zip(result["path"], result["path"][1:]):
        assert (a, b) in _VALID_EDGES, f"{a} -> {b} 는 그래프에 없는 edge"


def independently_recompute(path: list[str]) -> tuple[float, int, list[dict]]:
    """result를 전혀 신뢰하지 않고, 원본 station_graph.json만으로 path의
    비용/환승을 처음부터 다시 계산한다(구현 검증용 대조 기준).

    셀프 검증(구현이 자기 자신의 결과와만 일치)이 되지 않도록, shortest_path.py의
    로직을 재사용하지 않고 원본 데이터에서 line/base_time을 직접 뽑아 계산한다.
    """
    total = 0.0
    transfers: list[dict] = []
    prev_line: str | None = None

    for a, b in zip(path, path[1:]):
        edge = _RAW_EDGE_BY_PAIR[(a, b)]
        base_time = edge["time_min"]
        if _IS_TRANSFER_BY_ID[a] or _IS_TRANSFER_BY_ID[b]:
            base_time = round(base_time - TRANSFER_PENALTY_MIN, 2)

        cost = base_time
        if prev_line is not None and prev_line != edge["line"]:
            cost += TRANSFER_PENALTY_MIN
            transfers.append({"station": a, "from_line": prev_line, "to_line": edge["line"]})

        total += cost
        prev_line = edge["line"]

    return round(total, 2), len(transfers), transfers


def test_direct_two_stations_same_line():
    """1호선 인접역: 환승 없이 바로 연결되는 일반적인 경우."""
    result = find_shortest_path("소요산역", "동두천역")
    assert_path_is_valid(result, "소요산역", "동두천역")
    assert result["total_time_min"] > 0
    print("\n[일반 케이스]", result)


def test_transfer_required_between_two_lines():
    """4호선 혜화 -> 2호선/신분당선 강남: 최소 한 번 환승이 필요한 경우."""
    result = find_shortest_path("혜화", "강남")
    assert_path_is_valid(result, "혜화", "강남")
    assert result["total_time_min"] > 0
    assert result["transfer_count"] == len(result["transfers"])
    assert result["transfer_count"] > 0, "환승 없이 혜화->강남 경로가 나온 것은 예상과 다름"
    for t in result["transfers"]:
        assert t["from_line"] != t["to_line"]
        assert t["station"] in result["path"]
    print("\n[환승 케이스]", result)


def test_same_start_and_end_station():
    """출발역과 도착역이 같으면 소요시간 0, 경로는 해당 역 하나, 환승도 0."""
    result = find_shortest_path("강남", "강남")
    assert result == {
        "start": "강남",
        "end": "강남",
        "total_time_min": 0.0,
        "path": ["강남"],
        "transfer_count": 0,
        "transfers": [],
    }
    print("\n[동일역 케이스]", result)


def test_unknown_start_station_raises():
    with pytest.raises(StationNotFoundError):
        find_shortest_path("존재하지않는역", "강남")


def test_unknown_end_station_raises():
    with pytest.raises(StationNotFoundError):
        find_shortest_path("강남", "존재하지않는역")


def _write_graph(tmp_path, name, nodes, edges) -> StationGraph:
    graph = {"meta": {}, "nodes": nodes, "edges": edges}
    graph_file = tmp_path / name
    graph_file.write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")
    return StationGraph(graph_path=graph_file)


def test_same_line_pass_through_transfer_station_has_no_penalty(tmp_path):
    """환승역(is_transfer=True)이라도 같은 line으로 그냥 지나치면 페널티가 없어야 한다.

    A->B, B->C 모두 1호선. B는 is_transfer=True라서 station_graph.json 방식대로
    time_min에 4.5분이 구워져 있다고 가정(2.0+4.5=6.5, 3.0+4.5=7.5). 새 로직은
    이 구워진 페널티를 벗겨내고, 같은 line이라 실제 환승이 아니므로 다시
    더하지 않아야 한다 -> 기대 총 시간 = 2.0 + 3.0 = 5.0, transfer_count = 0.
    """
    nodes = [
        {"id": "A", "name": "A", "lines": ["1호선"], "is_transfer": False},
        {"id": "B", "name": "B", "lines": ["1호선"], "is_transfer": True},
        {"id": "C", "name": "C", "lines": ["1호선"], "is_transfer": False},
    ]
    edges = [
        {"from": "A", "to": "B", "line": "1호선", "distance_km": 1.0, "time_min": 6.5},
        {"from": "B", "to": "A", "line": "1호선", "distance_km": 1.0, "time_min": 6.5},
        {"from": "B", "to": "C", "line": "1호선", "distance_km": 1.0, "time_min": 7.5},
        {"from": "C", "to": "B", "line": "1호선", "distance_km": 1.0, "time_min": 7.5},
    ]
    graph = _write_graph(tmp_path, "same_line_pass_through.json", nodes, edges)

    result = graph.shortest_path("A", "C")
    assert result["total_time_min"] == 5.0
    assert result["transfer_count"] == 0
    assert result["transfers"] == []
    assert result["path"] == ["A", "B", "C"]


def test_real_line_change_adds_penalty_once_per_change(tmp_path):
    """is_transfer 플래그 없이도(A=B=C 전부 False) line이 실제로 바뀌면
    변경마다 정확히 4.5분이 붙어야 한다 -> 실제 환승 판단은 오직 line 비교여야 함."""
    nodes = [
        {"id": "A", "name": "A", "lines": ["1호선"], "is_transfer": False},
        {"id": "B", "name": "B", "lines": ["1호선", "2호선"], "is_transfer": False},
        {"id": "C", "name": "C", "lines": ["2호선"], "is_transfer": False},
    ]
    edges = [
        {"from": "A", "to": "B", "line": "1호선", "distance_km": 1.0, "time_min": 2.0},
        {"from": "B", "to": "A", "line": "1호선", "distance_km": 1.0, "time_min": 2.0},
        {"from": "B", "to": "C", "line": "2호선", "distance_km": 1.0, "time_min": 3.0},
        {"from": "C", "to": "B", "line": "2호선", "distance_km": 1.0, "time_min": 3.0},
    ]
    graph = _write_graph(tmp_path, "real_line_change.json", nodes, edges)

    result = graph.shortest_path("A", "C")
    assert result["total_time_min"] == 2.0 + 3.0 + TRANSFER_PENALTY_MIN
    assert result["transfer_count"] == 1
    assert result["transfers"] == [{"station": "B", "from_line": "1호선", "to_line": "2호선"}]


def test_hyehwa_to_gangnam_corrected_time_beats_naive_correction():
    """혜화->강남을 실제 station_graph.json에 대해 계산하고, 원본 데이터만으로
    독립적으로 재계산한 값과 정확히 일치하는지 검증한다.

    참고: 이전 turn에서 "기존 경로를 사후 보정"했을 때는 19.12 + 4x4.5 = 37.12분이
    나왔지만, 그건 예전(잘못된 가중치)의 Dijkstra가 고른 경로를 그대로 두고 시간만
    다시 계산한 값이다. 이번에 Dijkstra 자체가 올바른 가중치로 다시 탐색하므로,
    그보다 더 짧은 실제 최적 경로(충무로 환승)를 찾아내 37.12분보다 작아야 한다.
    """
    result = find_shortest_path("혜화", "강남")
    expected_total, expected_count, expected_transfers = independently_recompute(result["path"])

    assert result["total_time_min"] == expected_total
    assert result["transfer_count"] == expected_count
    assert result["transfers"] == expected_transfers
    # 예전 방식으로 "사후 보정"한 값(37.12분, 4회 환승)보다 같거나 짧아야 한다 -
    # Dijkstra가 전역 탐색으로 그보다 나쁜 경로를 고를 수는 없다.
    assert result["total_time_min"] <= 37.12
    assert result["transfer_count"] <= 4
    print("\n[혜화->강남 보정 결과]", result)


def test_gangnam_to_wangsimni_corrected_time_beats_naive_correction():
    """강남->왕십리(성동구청)도 동일하게 원본 데이터 기반 독립 재계산과 일치해야 하고,
    사후 보정값(29.44분, 2회 환승)보다 같거나 짧아야 한다."""
    result = find_shortest_path("강남", "왕십리(성동구청)")
    expected_total, expected_count, expected_transfers = independently_recompute(result["path"])

    assert result["total_time_min"] == expected_total
    assert result["transfer_count"] == expected_count
    assert result["transfers"] == expected_transfers
    assert result["total_time_min"] <= 29.44
    assert result["transfer_count"] <= 2
    print("\n[강남->왕십리(성동구청) 보정 결과]", result)


def test_shortest_times_from_matches_find_shortest_path():
    """get_shortest_times_from(start)["강남"]과
    find_shortest_path(start, "강남")["total_time_min"]이 같아야 한다."""
    times = get_shortest_times_from("혜화")
    direct = find_shortest_path("혜화", "강남")
    assert times["강남"] == direct["total_time_min"]


def test_shortest_times_from_start_itself_is_zero():
    times = get_shortest_times_from("혜화")
    assert times["혜화"] == 0.0


def test_shortest_times_from_covers_all_stations():
    """363개 역이 하나의 connected component이므로 전체 역이 다 포함돼야 한다."""
    times = get_shortest_times_from("혜화")
    assert len(times) == len(_RAW_GRAPH["nodes"])
    assert set(times.keys()) == set(_LINES_BY_STATION.keys())


def test_shortest_times_from_unknown_start_raises():
    with pytest.raises(StationNotFoundError):
        get_shortest_times_from("존재하지않는역")


def _build_isolated_graph(tmp_path) -> StationGraph:
    isolated_graph = {
        "meta": {},
        "nodes": [
            {"id": "A역", "name": "A역", "lines": ["1호선"], "is_transfer": False},
            {"id": "B역", "name": "B역", "lines": ["1호선"], "is_transfer": False},
            {"id": "C역", "name": "C역", "lines": ["2호선"], "is_transfer": False},
        ],
        # A-B만 연결되어 있고 C는 고립된 컴포넌트
        "edges": [
            {"from": "A역", "to": "B역", "line": "1호선", "distance_km": 1.0, "time_min": 2.0},
            {"from": "B역", "to": "A역", "line": "1호선", "distance_km": 1.0, "time_min": 2.0},
        ],
    }
    graph_file = tmp_path / "isolated_graph.json"
    graph_file.write_text(json.dumps(isolated_graph, ensure_ascii=False), encoding="utf-8")
    return StationGraph(graph_path=graph_file)


def test_no_path_between_disconnected_components(tmp_path):
    """연결되지 않은 두 역 사이는 NoPathFoundError를 발생시켜야 한다."""
    graph = _build_isolated_graph(tmp_path)
    with pytest.raises(NoPathFoundError):
        graph.shortest_path("A역", "C역")


def test_shortest_times_from_excludes_unreachable_stations(tmp_path):
    """그래프가 끊겨 있으면 도달 불가능한 역은 결과 dict에서 아예 빠져야 한다."""
    graph = _build_isolated_graph(tmp_path)
    times = graph.shortest_times_from("A역")
    assert times == {"A역": 0.0, "B역": 2.0}
    assert "C역" not in times
