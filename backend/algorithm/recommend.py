"""
여러 출발역을 기준으로 그래프의 모든 역을 후보로 평가해 Top-K 만남역을 추천한다.

Dijkstra는 candidate_evaluation.build_shortest_time_tables(origins)로 출발역별
1회만 실행한다. 이후 모든 후보역(최대 363개) 평가는 그 table을
candidate_evaluation.evaluate_candidate()에 그대로 넘겨 재사용하므로, 후보역
개수만큼 Dijkstra를 다시 돌리지 않는다.

score는 아직 하나의 가중치 조합을 정답으로 가정하지 않고, 다음 공식을
weights 인자로 조정 가능하게 구현한다(값이 낮을수록 좋은 후보):

    score = w_mean * mean_time + w_max * max_time + w_gap * time_gap

std_time은 결과에는 포함하되, 이번 단계의 기본 score 공식에는 사용하지 않는다.

score 계산 자체(_compute_score)와 후보 순회/table 재사용 구조는 그대로 두고,
그 위에 mode preset 레이어만 얹는다: mode로 미리 정의된 가중치 조합을 고르고,
필요하면 weights로 그 위에 덮어쓸 수 있다.
"""

from backend.algorithm.candidate_evaluation import build_shortest_time_tables, evaluate_candidate
from backend.algorithm.shortest_path import NoPathFoundError, all_station_ids

# recommendation mode preset. score가 낮을수록 좋은 후보이므로:
# - fair: gap(time_gap) 비중을 가장 높여 "다같이 비슷하게" 이동하는 역을 우선시.
# - fast: mean(mean_time) 비중을 가장 높여 "전체 이동시간 합"이 짧은 역을 우선시.
# - balanced: 기존 기본값과 동일한 절충안.
RECOMMENDATION_MODES: dict[str, dict[str, float]] = {
    "fair": {"w_mean": 0.2, "w_max": 0.3, "w_gap": 0.5},
    "fast": {"w_mean": 0.7, "w_max": 0.2, "w_gap": 0.1},
    "balanced": {"w_mean": 0.5, "w_max": 0.3, "w_gap": 0.2},
}
DEFAULT_MODE = "balanced"
# 하위 호환용 별칭: 기존에 DEFAULT_WEIGHTS를 직접 참조하던 코드/테스트가 계속 동작하도록 유지.
DEFAULT_WEIGHTS = RECOMMENDATION_MODES[DEFAULT_MODE]


def _compute_score(mean_time: float, max_time: float, time_gap: float, weights: dict) -> float:
    return (
        weights["w_mean"] * mean_time
        + weights["w_max"] * max_time
        + weights["w_gap"] * time_gap
    )


def recommend_meeting_stations(
    origins: list[str],
    top_k: int = 3,
    mode: str = DEFAULT_MODE,
    weights: dict | None = None,
) -> list[dict]:
    """origins 전원의 이동 부담이 가장 균형 잡힌 만남역 top_k개를 score 오름차순으로 반환한다.

    mode로 RECOMMENDATION_MODES 프리셋("fair"/"fast"/"balanced") 중 하나를 고르고,
    weights를 추가로 넘기면 그 프리셋 위에 일부 또는 전체 항목을 덮어쓴다.
    (예: mode="fair"에 weights={"w_max": 0.1}만 넘기면 w_mean/w_gap은 fair 프리셋 값을,
    w_max만 0.1을 쓴다.) weights를 전혀 안 넘기면 mode 프리셋을 그대로 쓴다.
    """
    if not origins:
        raise ValueError("origins는 최소 1명 이상이어야 합니다.")
    if top_k <= 0:
        raise ValueError("top_k는 1 이상이어야 합니다.")
    if mode not in RECOMMENDATION_MODES:
        raise ValueError(
            f"알 수 없는 mode입니다: {mode!r} (선택 가능: {sorted(RECOMMENDATION_MODES)})"
        )

    effective_weights = {**RECOMMENDATION_MODES[mode], **(weights or {})}

    # 출발역별 shortest-time table을 딱 한 번만 계산해서 모든 후보 평가에 재사용한다.
    # (StationNotFoundError는 존재하지 않는 출발역이 섞여 있으면 여기서 그대로 전파된다.)
    tables = build_shortest_time_tables(origins)

    candidates = all_station_ids()
    top_k = min(top_k, len(candidates))  # 후보 수보다 큰 top_k는 안전하게 잘라낸다.

    evaluated = []
    for candidate in candidates:
        try:
            result = evaluate_candidate(origins, candidate, shortest_time_tables=tables)
        except NoPathFoundError:
            # origins 중 일부에서 도달할 수 없는 후보는 만남 장소가 될 수 없으므로 제외한다.
            # (363개 역이 모두 연결된 실제 그래프에서는 실질적으로 발생하지 않는다.)
            continue

        score = round(
            _compute_score(
                result["mean_time"], result["max_time"], result["time_gap"], effective_weights
            ),
            2,
        )
        longest_travel = max(result["travel_times"], key=lambda t: t["time"])
        shortest_travel = min(result["travel_times"], key=lambda t: t["time"])

        evaluated.append(
            {
                "station": result["station"],
                "score": score,
                "mean_time": result["mean_time"],
                "max_time": result["max_time"],
                "min_time": result["min_time"],
                "time_gap": result["time_gap"],
                "std_time": result["std_time"],
                "travel_times": result["travel_times"],
                "longest_travel": longest_travel,
                "shortest_travel": shortest_travel,
                "mode": mode,
                "weights": effective_weights,
            }
        )

    evaluated.sort(key=lambda r: r["score"])
    return evaluated[:top_k]