"""backend/algorithm/recommend.py 검증 테스트.

실행: python -m pytest tests/test_recommend.py -v
"""

import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.algorithm import candidate_evaluation, recommend  # noqa: E402
from backend.algorithm.recommend import (  # noqa: E402
    DEFAULT_MODE,
    DEFAULT_WEIGHTS,
    RECOMMENDATION_MODES,
    recommend_meeting_stations,
)
from backend.algorithm.shortest_path import StationNotFoundError, all_station_ids  # noqa: E402

ORIGINS = ["혜화", "강남", "신촌(지하)"]
ASYMMETRIC_ORIGINS = ["강남", "강남", "역삼", "선릉", "혜화"]


def test_returns_exactly_top_k_results():
    results = recommend_meeting_stations(ORIGINS, top_k=5)
    assert len(results) == 5


def test_results_sorted_by_score_ascending():
    results = recommend_meeting_stations(ORIGINS, top_k=10)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores)


def test_score_matches_formula():
    results = recommend_meeting_stations(ORIGINS, top_k=10)
    for r in results:
        expected = round(
            DEFAULT_WEIGHTS["w_mean"] * r["mean_time"]
            + DEFAULT_WEIGHTS["w_max"] * r["max_time"]
            + DEFAULT_WEIGHTS["w_gap"] * r["time_gap"],
            2,
        )
        assert r["score"] == expected


def test_build_shortest_time_tables_called_exactly_once(monkeypatch):
    calls = []
    original = recommend.build_shortest_time_tables

    def counting_wrapper(origins):
        calls.append(origins)
        return original(origins)

    monkeypatch.setattr(recommend, "build_shortest_time_tables", counting_wrapper)

    recommend_meeting_stations(ORIGINS, top_k=3)

    assert len(calls) == 1


def test_dijkstra_not_rerun_per_candidate(monkeypatch):
    """후보역이 363개든 몇 개든, 실제 Dijkstra(get_shortest_times_from)는
    고유 출발역 개수만큼만 호출돼야 한다 - 후보 순회 중 재실행되면 안 된다."""
    calls = []
    original = candidate_evaluation.get_shortest_times_from

    def counting_wrapper(start):
        calls.append(start)
        return original(start)

    monkeypatch.setattr(candidate_evaluation, "get_shortest_times_from", counting_wrapper)

    recommend_meeting_stations(ORIGINS, top_k=3)

    assert len(calls) == len(set(ORIGINS))


def test_duplicate_origin_handled_correctly():
    origins_with_duplicate = ["혜화", "혜화", "강남"]
    results = recommend_meeting_stations(origins_with_duplicate, top_k=3)
    for r in results:
        assert len(r["travel_times"]) == 3
        hyehwa_entries = [t for t in r["travel_times"] if t["origin"] == "혜화"]
        assert len(hyehwa_entries) == 2


def test_changing_weights_changes_score():
    default_results = recommend_meeting_stations(ORIGINS, top_k=10)
    custom_results = recommend_meeting_stations(
        ORIGINS, top_k=10, weights={"w_mean": 0.0, "w_max": 0.0, "w_gap": 1.0}
    )

    # gap만 100% 반영하면 score는 정확히 time_gap과 같아야 한다.
    for r in custom_results:
        assert r["score"] == r["time_gap"]

    default_by_station = {r["station"]: r["score"] for r in default_results}
    custom_by_station = {r["station"]: r["score"] for r in custom_results}
    common_stations = set(default_by_station) & set(custom_by_station)
    assert any(default_by_station[s] != custom_by_station[s] for s in common_stations)


def test_top_k_larger_than_candidate_count_is_clamped():
    total_candidates = len(all_station_ids())
    results = recommend_meeting_stations(ORIGINS, top_k=total_candidates + 1000)
    # 363개 역이 모두 하나의 connected component이므로 전체 후보가 다 나와야 한다.
    assert len(results) == total_candidates


def test_empty_origins_raises_value_error():
    with pytest.raises(ValueError):
        recommend_meeting_stations([], top_k=3)


def test_non_positive_top_k_raises_value_error():
    with pytest.raises(ValueError):
        recommend_meeting_stations(ORIGINS, top_k=0)
    with pytest.raises(ValueError):
        recommend_meeting_stations(ORIGINS, top_k=-1)


def test_unknown_origin_raises_station_not_found_error():
    with pytest.raises(StationNotFoundError):
        recommend_meeting_stations(["존재하지않는역", "강남"], top_k=3)


def test_default_mode_is_balanced():
    """mode를 안 주면 balanced 프리셋(=DEFAULT_WEIGHTS)을 써야 한다."""
    default_results = recommend_meeting_stations(ORIGINS, top_k=5)
    explicit_results = recommend_meeting_stations(ORIGINS, top_k=5, mode="balanced")

    assert default_results == explicit_results
    for r in default_results:
        assert r["mode"] == "balanced" == DEFAULT_MODE
        assert r["weights"] == DEFAULT_WEIGHTS == RECOMMENDATION_MODES["balanced"]


@pytest.mark.parametrize("mode", ["fair", "fast", "balanced"])
def test_each_mode_reports_correct_weights_and_matches_score_formula(mode):
    results = recommend_meeting_stations(ASYMMETRIC_ORIGINS, top_k=5, mode=mode)
    expected_weights = RECOMMENDATION_MODES[mode]

    for r in results:
        assert r["mode"] == mode
        assert r["weights"] == expected_weights
        expected_score = round(
            expected_weights["w_mean"] * r["mean_time"]
            + expected_weights["w_max"] * r["max_time"]
            + expected_weights["w_gap"] * r["time_gap"],
            2,
        )
        assert r["score"] == expected_score


def test_invalid_mode_raises_value_error():
    with pytest.raises(ValueError):
        recommend_meeting_stations(ORIGINS, top_k=3, mode="fastest_ever")


def test_weights_override_mode_preset():
    """mode로 프리셋을 고르되, weights를 넘기면 그 프리셋 위에 덮어써야 한다."""
    results = recommend_meeting_stations(
        ASYMMETRIC_ORIGINS, top_k=5, mode="fair", weights={"w_mean": 1.0, "w_max": 0.0, "w_gap": 0.0}
    )
    for r in results:
        # w_mean=1.0, 나머지 0으로 완전히 덮어썼으므로 score는 mean_time과 정확히 같아야 한다.
        assert r["score"] == r["mean_time"]
        assert r["weights"] == {"w_mean": 1.0, "w_max": 0.0, "w_gap": 0.0}


def test_fair_and_fast_modes_produce_different_rankings_for_asymmetric_origins():
    """강남 편향(강남x2, 역삼, 선릉, 혜화 1명)처럼 비대칭 입력에서는
    fair(gap 중시)와 fast(mean 중시) 모드의 추천 결과가 실제로 달라져야 한다."""
    fair_results = recommend_meeting_stations(ASYMMETRIC_ORIGINS, top_k=5, mode="fair")
    fast_results = recommend_meeting_stations(ASYMMETRIC_ORIGINS, top_k=5, mode="fast")

    fair_stations = [r["station"] for r in fair_results]
    fast_stations = [r["station"] for r in fast_results]

    # top1부터 달라야 "성향이 실제로 반영됐다"고 볼 수 있다.
    assert fair_results[0]["station"] != fast_results[0]["station"]
    assert fair_stations != fast_stations