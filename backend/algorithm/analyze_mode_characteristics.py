"""
fair / fast / balanced 3개 recommendation mode의 특성을 체계적으로 검증하는
분석 스크립트.

기존 알고리즘(backend/algorithm/recommend.py 등)은 전혀 수정하지 않고,
15가지 상황 유형(대칭/근거리/원거리/균형/편향/극단편향/클러스터/분산 등)에
recommend_meeting_stations()를 그대로 호출해 mode별 Top-3를 비교 출력한다.

마지막에는 케이스별로
  - 세 mode가 모두 같은 1위를 골랐는지
  - fair/fast의 1위가 다른지
  - fair가 fast 대비 time_gap을 얼마나 줄였는지
  - fast가 fair 대비 mean_time을 얼마나 줄였는지
  - balanced가 그 사이 절충인지
를 자동 요약하고, "fair -> gap 개선 / fast -> mean 개선" 패턴이 비대칭
케이스에서 실제로 나타나는 비율을 집계한다.

실행:
    python backend/algorithm/analyze_mode_characteristics.py
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.algorithm.recommend import recommend_meeting_stations  # noqa: E402

MODES = ["fair", "fast", "balanced"]

# 전부 station_graph.json에 실제 존재하는 id로만 구성했다(사전에 그래프에서 조회해 확인).
CASES = {
    "1. 2인 대칭": ["신촌(지하)", "건대입구"],
    "2. 2인 근거리": ["강남", "역삼"],
    "3. 2인 원거리": ["소요산역", "인천역"],
    "4. 3인 균형": ["혜화", "강남", "신촌(지하)"],
    "5. 3인 편향": ["강남", "역삼", "신촌(지하)"],
    "6. 3인 극단 편향": ["강남", "역삼", "소요산역"],
    "7. 4인 2:2 대칭": ["이대", "홍대입구", "건대입구", "강변(동서울터미널)"],
    "8. 4인 3:1 편향": ["강남", "역삼", "선릉", "혜화"],
    "9. 5인 4:1 편향": ["강남", "강남", "역삼", "선릉", "혜화"],
    "10. 5인 넓게 분산": ["소요산역", "인천역", "하남검단산", "오금", "강남"],
    "11. 6인 3:3 양쪽 클러스터": ["신촌(지하)", "이대", "홍대입구", "건대입구", "강변(동서울터미널)", "잠실(송파구청)"],
    "12. 6인 5:1 극단 편향": ["강남", "강남", "강남", "역삼", "선릉", "소요산역"],
    "13. 전원 동일 출발역": ["신촌(지하)", "신촌(지하)", "신촌(지하)"],
    "14. 서로 인접한 역들": ["시청", "종각", "종로3가(탑골공원)", "종로5가"],
    "15. 여러 노선이 섞인 분산": ["소요산역", "방화", "노원", "상일동", "오금"],
}


def print_top3(mode: str, results: list[dict]) -> None:
    weights = results[0]["weights"] if results else {}
    print(f"--- mode: {mode}  (w_mean={weights.get('w_mean')}, "
          f"w_max={weights.get('w_max')}, w_gap={weights.get('w_gap')}) ---")
    print(f"{'station':22s} {'score':>7s} {'mean':>7s} {'max':>7s} {'gap':>7s} {'std':>7s}")
    for r in results:
        print(
            f"{r['station']:22s} {r['score']:7.2f} {r['mean_time']:7.2f} "
            f"{r['max_time']:7.2f} {r['time_gap']:7.2f} {r['std_time']:7.2f}"
        )
    top1 = results[0]
    print(f"   1위({top1['station']}) 사용자별 travel_time: "
          + ", ".join(f"{t['origin']}={t['time']}" for t in top1["travel_times"]))
    print()


def run_case(name: str, origins: list[str]) -> dict:
    print("=" * 72)
    print(f"CASE: {name}")
    print(f"Origins: {' / '.join(origins)}")
    print(f"사용자 수: {len(origins)}")
    print()

    results_by_mode = {}
    for mode in MODES:
        results = recommend_meeting_stations(origins, top_k=3, mode=mode)
        results_by_mode[mode] = results
        print_top3(mode, results)

    return results_by_mode


def summarize(name: str, results_by_mode: dict) -> dict:
    fair1 = results_by_mode["fair"][0]
    fast1 = results_by_mode["fast"][0]
    bal1 = results_by_mode["balanced"][0]

    all_same = fair1["station"] == fast1["station"] == bal1["station"]
    fair_fast_differ = fair1["station"] != fast1["station"]

    gap_improvement = round(fast1["time_gap"] - fair1["time_gap"], 2)  # 양수면 fair가 gap을 줄인 것
    mean_improvement = round(fair1["mean_time"] - fast1["mean_time"], 2)  # 양수면 fast가 mean을 줄인 것

    mean_lo, mean_hi = sorted([fair1["mean_time"], fast1["mean_time"]])
    gap_lo, gap_hi = sorted([fair1["time_gap"], fast1["time_gap"]])
    balanced_mean_between = mean_lo <= bal1["mean_time"] <= mean_hi
    balanced_gap_between = gap_lo <= bal1["time_gap"] <= gap_hi

    return {
        "case": name,
        "fair_station": fair1["station"],
        "fast_station": fast1["station"],
        "balanced_station": bal1["station"],
        "all_same": all_same,
        "fair_fast_differ": fair_fast_differ,
        "gap_improvement_by_fair": gap_improvement,
        "mean_improvement_by_fast": mean_improvement,
        "balanced_mean_between": balanced_mean_between,
        "balanced_gap_between": balanced_gap_between,
    }


def print_summary_table(summaries: list[dict]) -> None:
    print("=" * 72)
    print("SUMMARY")
    print("=" * 72)
    header = (
        f"{'case':28s} {'all_same':>8s} {'ff_diff':>7s} {'gap_imp(fair)':>13s} "
        f"{'mean_imp(fast)':>14s} {'bal_between(mean/gap)':>22s}"
    )
    print(header)
    print("-" * len(header))
    for s in summaries:
        between = f"{str(s['balanced_mean_between']):>5s}/{str(s['balanced_gap_between']):<5s}"
        print(
            f"{s['case']:28s} {str(s['all_same']):>8s} {str(s['fair_fast_differ']):>7s} "
            f"{s['gap_improvement_by_fair']:13.2f} {s['mean_improvement_by_fast']:14.2f} "
            f"{between:>22s}"
        )
    print()

    skewed = [s for s in summaries if s["fair_fast_differ"]]
    if skewed:
        gap_pattern_ok = sum(1 for s in skewed if s["gap_improvement_by_fair"] >= 0)
        mean_pattern_ok = sum(1 for s in skewed if s["mean_improvement_by_fast"] >= 0)
        both_between_ok = sum(
            1 for s in skewed if s["balanced_mean_between"] and s["balanced_gap_between"]
        )
        n = len(skewed)
        print(f"fair/fast의 1위가 갈린 케이스: {n}개")
        print(f"  - 그 중 fair가 fast보다 1위의 time_gap을 줄이거나 같음: {gap_pattern_ok}/{n}")
        print(f"  - 그 중 fast가 fair보다 1위의 mean_time을 줄이거나 같음: {mean_pattern_ok}/{n}")
        print(f"  - 그 중 balanced의 1위가 mean/gap 둘 다 fair-fast 사이에 낌: {both_between_ok}/{n}")
    else:
        print("fair/fast의 1위가 갈린 케이스가 없습니다.")


def main() -> None:
    summaries = []
    for name, origins in CASES.items():
        results_by_mode = run_case(name, origins)
        summaries.append(summarize(name, results_by_mode))

    print_summary_table(summaries)


if __name__ == "__main__":
    main()