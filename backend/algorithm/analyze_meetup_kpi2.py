"""
KPI② "참여자 간 이동시간 편차 감소"를 사용자 데이터 없이 오프라인으로 검증하는 배치 스크립트.

추천 알고리즘(backend/algorithm/recommend.py)이 고른 역과, "이 서비스 없이 임의로
정했을 때"(그래프의 모든 역 중 무작위 선택)의 std_time/time_gap을 여러 출발역
시나리오에 대해 비교한다. 실제 유저 트래픽이나 GA4 없이, 코드 실행만으로 바로
결과를 얻을 수 있다. 기존 알고리즘 코드는 전혀 수정하지 않는다.

실행:
    python backend/algorithm/analyze_meetup_kpi2.py
"""

import random
import statistics
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.algorithm.candidate_evaluation import (  # noqa: E402
    build_shortest_time_tables,
    evaluate_candidate,
)
from backend.algorithm.recommend import recommend_meeting_stations  # noqa: E402
from backend.algorithm.shortest_path import NoPathFoundError, all_station_ids  # noqa: E402

RANDOM_SEED = 42
RANDOM_SAMPLE_SIZE = 30
ALGO_MODE = "fair"  # time_gap 최소화가 목적인 모드라 KPI② 비교의 기준으로 삼는다.

cases = {
    "강남권 편향 (강남x2, 역삼, 선릉, 혜화x1)": ["강남", "강남", "역삼", "선릉", "혜화"],
    "대칭 (신촌x2, 잠실x2)": ["신촌(지하)", "신촌(지하)", "잠실(송파구청)", "잠실(송파구청)"],
    "5인 분산 (혜화/강남/잠실/신촌/노량진)": ["혜화", "강남", "잠실(송파구청)", "신촌(지하)", "노량진"],
}


def random_baseline(origins: list[str], rng: random.Random) -> dict:
    """origins에 대해 후보역을 무작위로 골랐을 때의 평균 std_time/time_gap."""
    tables = build_shortest_time_tables(origins)
    candidates = all_station_ids()
    sample = rng.sample(candidates, min(RANDOM_SAMPLE_SIZE, len(candidates)))

    std_times, time_gaps = [], []
    for candidate in sample:
        try:
            result = evaluate_candidate(origins, candidate, shortest_time_tables=tables)
        except NoPathFoundError:
            continue
        std_times.append(result["std_time"])
        time_gaps.append(result["time_gap"])

    return {
        "std_time": round(statistics.fmean(std_times), 2),
        "time_gap": round(statistics.fmean(time_gaps), 2),
        "n": len(std_times),
    }


def print_case(name: str, origins: list[str], rng: random.Random) -> None:
    print("=" * 78)
    print(f"CASE: {name}")
    print(f"Origins: {' / '.join(origins)}")

    algo_top1 = recommend_meeting_stations(origins, top_k=1, mode=ALGO_MODE)[0]
    baseline = random_baseline(origins, rng)

    print(f"\n[알고리즘 추천 ({ALGO_MODE} 모드)] {algo_top1['station']}")
    print(f"  std_time = {algo_top1['std_time']:.2f}분, time_gap = {algo_top1['time_gap']:.2f}분")

    print(f"\n[랜덤 베이스라인] 무작위 역 {baseline['n']}개 평균")
    print(f"  std_time = {baseline['std_time']:.2f}분, time_gap = {baseline['time_gap']:.2f}분")

    std_reduction = (baseline["std_time"] - algo_top1["std_time"]) / baseline["std_time"] * 100
    gap_reduction = (baseline["time_gap"] - algo_top1["time_gap"]) / baseline["time_gap"] * 100
    print(f"\n  => std_time {std_reduction:.1f}% 감소, time_gap {gap_reduction:.1f}% 감소")
    print()

    return {"std_reduction": std_reduction, "gap_reduction": gap_reduction}


def main() -> None:
    rng = random.Random(RANDOM_SEED)
    reductions = []
    for name, origins in cases.items():
        reductions.append(print_case(name, origins, rng))

    avg_std = statistics.fmean(r["std_reduction"] for r in reductions)
    avg_gap = statistics.fmean(r["gap_reduction"] for r in reductions)
    print("=" * 78)
    print(f"전체 시나리오 평균: std_time {avg_std:.1f}% 감소, time_gap {avg_gap:.1f}% 감소")
    print(f"(무작위 후보 {RANDOM_SAMPLE_SIZE}개 샘플, seed={RANDOM_SEED})")


if __name__ == "__main__":
    main()
