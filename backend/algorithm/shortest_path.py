"""
station_graph.json 기반 두 역 사이 최단 소요시간 경로 계산 (Dijkstra).

station_graph.json의 edge time_min에는 그래프 생성 단계(data/scripts/build_graph.py)에서
"실제 노선 변경 여부와 무관하게 환승역을 통과하기만 해도" 4.5분 환승 페널티가
구워져 있다(자세한 근거는 backend/algorithm/debug_transfer_penalty.py 참고).
이 모듈은 그 잘못된 페널티를 걷어내 순수 이동시간(base_time)을 복원한 뒤,
Dijkstra 탐색 중 "직전 edge의 line != 다음 edge의 line"일 때만 환승 페널티를
다시 매긴다. 이를 위해 탐색 상태를 station이 아니라 (station, 도착 line)으로
확장한다 - 역명 하나가 여러 노선을 합친 단일 node이기 때문에, 이 상태 확장
없이는 "환승역을 그냥 지나침"과 "실제 환승"을 구분할 방법이 없다.

station_graph.json, build_graph.py는 이 모듈에서 읽기만 하고 수정하지 않는다.

사용법:
    from backend.algorithm.shortest_path import find_shortest_path, get_shortest_times_from

    result = find_shortest_path("혜화", "강남")
    # {"start": "혜화", "end": "강남", "total_time_min": 37.12, "path": [...],
    #  "transfer_count": 4, "transfers": [{"station": ..., "from_line": ..., "to_line": ...}, ...]}

    times = get_shortest_times_from("혜화")
    # {"혜화": 0.0, "동대문": 3.2, "왕십리": 15.4, ...}  # 도달 가능한 모든 역
"""

import heapq
import json
from itertools import count
from pathlib import Path

GRAPH_PATH = Path(__file__).resolve().parents[2] / "data" / "station_graph.json"

# data/scripts/build_graph.py의 TRANSFER_PENALTY_MIN과 동일한 값.
# 여기서는 두 군데에 쓰인다: (1) __init__에서 잘못 구워진 페널티를 제거할 때,
# (2) _dijkstra에서 실제 line 변경이 확인된 순간에만 다시 더할 때.
TRANSFER_PENALTY_MIN = 4.5

# 아직 아무 line도 타지 않은 출발 상태를 표시하는 sentinel.
# "처음 탑승하는 edge에는 환승 페널티가 없다"는 규칙을 이 값으로 구현한다.
NOT_BOARDED = None

State = tuple[str, str | None]  # (station, current_line)


class StationNotFoundError(ValueError):
    """그래프에 존재하지 않는 역 이름을 조회했을 때 발생."""


class NoPathFoundError(ValueError):
    """두 역 사이에 경로가 존재하지 않을 때 발생."""


class StationGraph:
    """station_graph.json을 한 번만 읽어 인접 리스트로 재사용하는 그래프.

    중간역 추천 단계에서 최단경로 계산을 매우 많이 반복 호출할 예정이므로,
    JSON 로딩 및 인접 리스트 구성 비용을 인스턴스당 한 번만 지불하도록 만든다.
    """

    def __init__(self, graph_path: Path = GRAPH_PATH):
        with open(graph_path, encoding="utf-8") as f:
            data = json.load(f)

        self.station_ids: set[str] = {node["id"] for node in data["nodes"]}
        is_transfer_by_id = {node["id"]: node["is_transfer"] for node in data["nodes"]}

        # (도착역, 순수 이동시간(base_time), line) 튜플로 인접 리스트를 구성한다.
        # base_time은 build_graph.py가 구운 "통과 기반" 페널티를 제거한 값이다.
        self._adjacency: dict[str, list[tuple[str, float, str]]] = {
            sid: [] for sid in self.station_ids
        }
        for edge in data["edges"]:
            src, dst, line = edge["from"], edge["to"], edge["line"]
            base_time = edge["time_min"]
            if is_transfer_by_id[src] or is_transfer_by_id[dst]:
                base_time -= TRANSFER_PENALTY_MIN
            self._adjacency[src].append((dst, round(base_time, 2), line))

    def has_station(self, station_id: str) -> bool:
        return station_id in self.station_ids

    def _dijkstra(
        self, start: str, target: str | None = None
    ) -> tuple[dict[State, float], dict[State, State]]:
        """(station, current_line) 상태 공간에서 Dijkstra를 1회 실행한다.

        edge 비용은 base_time에, "직전 상태의 line과 다음 edge의 line이 다를
        때만" TRANSFER_PENALTY_MIN을 더해 계산한다(출발 직후 첫 edge는 직전
        line이 없으므로 페널티 없음).

        target이 주어지면 station == target인 상태가 처음 확정(pop)되는 즉시
        종료한다 — Dijkstra는 항상 거리가 작은 상태부터 확정하므로, station이
        target과 같은 상태가 처음 나오는 시점이 곧 (도착 line과 무관한) 전역
        최소 거리다. target이 None이면 도달 가능한 모든 상태를 끝까지 계산한다.

        반환:
          finalized: 각 상태가 확정된 시점의 최단 거리 {(station, line): dist}
          prev: 경로 복원을 위한 이전 상태 {(station, line): (prev_station, prev_line)}

        start를 호출하는 쪽에서 이미 검증했다고 가정하므로 이 메서드는 역
        존재 여부를 검사하지 않는다.
        """
        start_state: State = (start, NOT_BOARDED)
        dist: dict[State, float] = {start_state: 0.0}
        prev: dict[State, State] = {}
        finalized: dict[State, float] = {}
        visited: set[State] = set()
        tie_breaker = count()  # 힙에서 (dist, station, line) 비교 시 line=None 충돌 방지
        pq: list[tuple[float, int, str, str | None]] = [(0.0, next(tie_breaker), start, NOT_BOARDED)]

        while pq:
            d, _, u, cur_line = heapq.heappop(pq)
            state = (u, cur_line)
            if state in visited:
                continue
            visited.add(state)
            finalized[state] = d

            if target is not None and u == target:
                break

            for v, base_time, edge_line in self._adjacency[u]:
                cost = base_time
                if cur_line is not None and cur_line != edge_line:
                    cost += TRANSFER_PENALTY_MIN
                nd = d + cost
                new_state = (v, edge_line)
                if new_state not in dist or nd < dist[new_state]:
                    dist[new_state] = nd
                    prev[new_state] = state
                    heapq.heappush(pq, (nd, next(tie_breaker), v, edge_line))

        return finalized, prev

    def shortest_path(self, start: str, end: str) -> dict:
        """start -> end 최소 예상 소요시간 경로를 Dijkstra로 계산한다.

        실제 line 변경이 일어난 지점만 환승으로 집계해 transfer_count/transfers를
        함께 반환한다.
        """
        if not self.has_station(start):
            raise StationNotFoundError(f"존재하지 않는 역입니다: {start}")
        if not self.has_station(end):
            raise StationNotFoundError(f"존재하지 않는 역입니다: {end}")

        if start == end:
            return {
                "start": start,
                "end": end,
                "total_time_min": 0.0,
                "path": [start],
                "transfer_count": 0,
                "transfers": [],
            }

        finalized, prev = self._dijkstra(start, target=end)

        end_states = [state for state in finalized if state[0] == end]
        if not end_states:
            raise NoPathFoundError(f"{start} -> {end} 경로를 찾을 수 없습니다.")
        end_state = end_states[0]  # target 조기 종료 덕분에 항상 하나뿐인 전역 최소 상태

        states_path = [end_state]
        while states_path[-1] != (start, NOT_BOARDED):
            states_path.append(prev[states_path[-1]])
        states_path.reverse()

        path = [station for station, _line in states_path]

        transfers = []
        for i in range(1, len(states_path)):
            prev_line = states_path[i - 1][1]
            cur_line = states_path[i][1]
            if prev_line is not None and cur_line != prev_line:
                transfers.append(
                    {"station": states_path[i - 1][0], "from_line": prev_line, "to_line": cur_line}
                )

        return {
            "start": start,
            "end": end,
            "total_time_min": round(finalized[end_state], 2),
            "path": path,
            "transfer_count": len(transfers),
            "transfers": transfers,
        }

    def shortest_times_from(self, start: str) -> dict[str, float]:
        """start에서 그래프 내 모든 도달 가능한 역까지의 최소 예상 소요시간(분).

        중간역 추천 단계에서 후보역마다 shortest_path를 따로 호출하면 같은
        출발역에 대해 Dijkstra를 반복 실행하게 되므로, 한 번의 실행으로 전체
        역의 소요시간을 미리 계산해 dict로 반환한다(빠른 lookup용). 같은 역이라도
        도착 line에 따라 상태가 여러 개일 수 있으므로, 역별로 그 중 최솟값만 취한다.
        """
        if not self.has_station(start):
            raise StationNotFoundError(f"존재하지 않는 역입니다: {start}")

        finalized, _ = self._dijkstra(start)

        times: dict[str, float] = {}
        for (station, _line), d in finalized.items():
            if station not in times or d < times[station]:
                times[station] = d
        return {station: round(t, 2) for station, t in times.items()}


_default_graph: StationGraph | None = None


def _get_default_graph() -> StationGraph:
    global _default_graph
    if _default_graph is None:
        _default_graph = StationGraph()
    return _default_graph


def find_shortest_path(start: str, end: str) -> dict:
    """station_graph.json 기준 start -> end 최소 예상 소요시간 경로를 계산한다.

    모듈 전역에 캐싱된 StationGraph를 재사용하므로, 반복 호출해도 매번
    JSON을 다시 읽거나 인접 리스트를 다시 만들지 않는다.
    """
    return _get_default_graph().shortest_path(start, end)


def get_shortest_times_from(start: str) -> dict[str, float]:
    """station_graph.json 기준 start에서 모든 역까지의 최소 예상 소요시간(분)을,
    한 번의 Dijkstra 실행으로 계산해 {역명: 소요시간} dict로 반환한다.

    모듈 전역에 캐싱된 StationGraph를 재사용하므로, 여러 출발역에 대해
    반복 호출해도 그래프를 다시 읽지 않는다.
    """
    return _get_default_graph().shortest_times_from(start)


def station_exists(station_id: str) -> bool:
    """station_graph.json 기준 해당 역이 그래프에 존재하는지 여부.

    후보역 평가 등에서 Dijkstra 없이 역 이름 유효성만 확인하고 싶을 때 쓴다.
    """
    return _get_default_graph().has_station(station_id)


def all_station_ids() -> list[str]:
    """station_graph.json에 있는 모든 역 id 목록.

    중간역 추천에서 "그래프의 모든 역을 후보로 순회"할 때 후보 목록으로 쓴다.
    """
    return sorted(_get_default_graph().station_ids)