"""
여러 사용자의 출발역을 기준으로 특정 후보역이 만남 장소로 얼마나 적절한지
평가하는 이동시간 통계 계산.

Dijkstra 실행 자체는 backend.algorithm.shortest_path.get_shortest_times_from()에
위임한다. 이 모듈은 출발역별 shortest-time table을 후보역 평가에 재사용하는
역할만 담당한다 — 이후 모든 363개 역을 후보로 반복 평가할 예정이므로, table은
후보역 순회 바깥에서 한 번만 만들어 넘겨 쓸 수 있게 설계했다.

아직 추천 점수(score) 계산이나 후보역 전체 순회/Top-K 선정은 이 모듈의
범위가 아니다.

사용법:
    from backend.algorithm.candidate_evaluation import (
        build_shortest_time_tables,
        evaluate_candidate,
    )

    origins = ["혜화", "강남", "신촌(지하)"]

    # 후보역을 여러 번 평가할 때는 table을 한 번만 만들어 재사용한다.
    tables = build_shortest_time_tables(origins)
    result = evaluate_candidate(origins, "왕십리(성동구청)", tables)

    # table을 직접 넘기지 않으면 evaluate_candidate가 내부에서 만든다.
    result = evaluate_candidate(origins, "왕십리(성동구청)")
"""

import statistics

from backend.algorithm.shortest_path import (
    NoPathFoundError,
    StationNotFoundError,
    get_shortest_times_from,
    station_exists,
)


def build_shortest_time_tables(origins: list[str]) -> dict[str, dict[str, float]]:
    """출발역별 {도달역: 소요시간} table을 만든다.

    같은 출발역이 여러 사용자에게서 중복돼도 Dijkstra는 고유 출발역당
    한 번만 실행한다. 존재하지 않는 출발역이 섞여 있으면
    get_shortest_times_from()이 그대로 StationNotFoundError를 낸다.
    """
    unique_origins = dict.fromkeys(origins)  # 입력 순서를 보존한 중복 제거
    return {origin: get_shortest_times_from(origin) for origin in unique_origins}


def evaluate_candidate(
    origins: list[str],
    candidate: str,
    shortest_time_tables: dict[str, dict[str, float]] | None = None,
) -> dict:
    """origins 각각에서 candidate까지의 이동시간과 그 통계를 계산한다.

    shortest_time_tables를 미리 만들어 넘기면(예: 모든 후보역을 순회하는
    상위 루프에서 build_shortest_time_tables(origins)를 한 번만 호출) 이
    함수는 Dijkstra를 다시 실행하지 않고 dict lookup만 수행한다. 넘기지
    않으면 이 함수가 직접 table을 만든다.
    """
    if not origins:
        raise ValueError("origins는 최소 1명 이상이어야 합니다.")

    if not station_exists(candidate):
        raise StationNotFoundError(f"존재하지 않는 역입니다: {candidate}")

    if shortest_time_tables is None:
        shortest_time_tables = build_shortest_time_tables(origins)

    travel_times = []
    times: list[float] = []
    for origin in origins:
        table = shortest_time_tables.get(origin)
        if table is None:
            # 호출자가 넘긴 table에 이 origin이 빠져 있으면 직접 계산한다.
            # (존재하지 않는 origin이면 여기서 StationNotFoundError가 그대로 전파된다.)
            table = get_shortest_times_from(origin)

        if candidate not in table:
            raise NoPathFoundError(f"{origin} -> {candidate} 경로를 찾을 수 없습니다.")

        time = table[candidate]
        travel_times.append({"origin": origin, "time": time})
        times.append(time)

    return {
        "station": candidate,
        "travel_times": travel_times,
        "mean_time": round(statistics.fmean(times), 2),
        "max_time": max(times),
        "min_time": min(times),
        "time_gap": round(max(times) - min(times), 2),
        "std_time": round(statistics.pstdev(times), 2),
    }