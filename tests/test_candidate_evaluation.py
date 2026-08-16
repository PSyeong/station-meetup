"""backend/algorithm/candidate_evaluation.py 검증 테스트.

실행: python -m pytest tests/test_candidate_evaluation.py -v
"""

import statistics
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.algorithm import candidate_evaluation  # noqa: E402
from backend.algorithm.candidate_evaluation import (  # noqa: E402
    build_shortest_time_tables,
    evaluate_candidate,
)
from backend.algorithm.shortest_path import StationNotFoundError  # noqa: E402

# station_graph.json에서 "신촌"/"왕십리"는 원본 표기가 그대로 남아 있어
# 각각 "신촌(지하)", "왕십리(성동구청)"로만 존재한다(2호선 신촌역, 왕십리역).
ORIGINS = ["혜화", "강남", "신촌(지하)"]
CANDIDATE = "왕십리(성동구청)"


def test_evaluate_candidate_computes_stats_for_multiple_origins():
    result = evaluate_candidate(ORIGINS, CANDIDATE)

    assert result["station"] == CANDIDATE
    assert {t["origin"] for t in result["travel_times"]} == set(ORIGINS)
    assert len(result["travel_times"]) == len(ORIGINS)
    for entry in result["travel_times"]:
        assert entry["time"] > 0
    print("\n[3개 출발역 평가]", result)


def test_mean_max_min_gap_match_manual_calculation():
    result = evaluate_candidate(ORIGINS, CANDIDATE)
    times = [entry["time"] for entry in result["travel_times"]]

    assert result["mean_time"] == round(sum(times) / len(times), 2)
    assert result["max_time"] == max(times)
    assert result["min_time"] == min(times)
    assert result["time_gap"] == round(max(times) - min(times), 2)


def test_std_time_matches_population_stdev():
    result = evaluate_candidate(ORIGINS, CANDIDATE)
    times = [entry["time"] for entry in result["travel_times"]]

    assert result["std_time"] == round(statistics.pstdev(times), 2)


def test_duplicate_origin_is_counted_per_user():
    origins_with_duplicate = ["혜화", "혜화", "강남"]
    result = evaluate_candidate(origins_with_duplicate, CANDIDATE)

    assert len(result["travel_times"]) == 3
    hyehwa_entries = [t for t in result["travel_times"] if t["origin"] == "혜화"]
    assert len(hyehwa_entries) == 2
    # 같은 출발역이므로 두 사용자의 이동시간 값은 동일해야 한다.
    assert hyehwa_entries[0]["time"] == hyehwa_entries[1]["time"]
    print("\n[중복 출발역 평가]", result)


def test_unknown_candidate_raises_station_not_found_error():
    with pytest.raises(StationNotFoundError):
        evaluate_candidate(ORIGINS, "존재하지않는역")


def test_unknown_origin_raises_station_not_found_error():
    with pytest.raises(StationNotFoundError):
        evaluate_candidate(["존재하지않는역", "강남"], CANDIDATE)


def test_build_shortest_time_tables_dedupes_dijkstra_calls_per_origin(monkeypatch):
    """동일 출발역이 여러 번 있어도 Dijkstra는 고유 출발역당 한 번만 실행돼야 한다."""
    calls: list[str] = []
    original = candidate_evaluation.get_shortest_times_from

    def counting_wrapper(start):
        calls.append(start)
        return original(start)

    monkeypatch.setattr(candidate_evaluation, "get_shortest_times_from", counting_wrapper)

    build_shortest_time_tables(["혜화", "혜화", "강남", "혜화"])

    assert calls.count("혜화") == 1
    assert calls.count("강남") == 1


def test_evaluate_candidate_reuses_precomputed_tables(monkeypatch):
    """shortest_time_tables를 미리 넘기면 evaluate_candidate가 추가로
    Dijkstra를 실행하지 않아야 한다(다수 후보역 반복 평가 시 재사용 목적)."""
    tables = build_shortest_time_tables(ORIGINS)

    def fail_if_called(start):
        raise AssertionError(f"get_shortest_times_from가 재호출됨: {start}")

    monkeypatch.setattr(candidate_evaluation, "get_shortest_times_from", fail_if_called)

    result = evaluate_candidate(ORIGINS, CANDIDATE, shortest_time_tables=tables)
    assert result["station"] == CANDIDATE