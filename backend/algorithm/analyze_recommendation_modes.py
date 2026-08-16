"""
recommend_meeting_stations()의 mode preset(fair/fast/balanced)이 실제로
추천 성향을 다르게 만드는지 확인하기 위한 분석 스크립트.

기존 알고리즘(backend/algorithm/recommend.py 등)은 전혀 수정하지 않고,
비대칭 출발역 조합 여러 개에 대해 세 mode의 Top-3 결과를 나란히 비교해 출력한다.

실행:
    python backend/algorithm/analyze_recommendation_modes.py
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.algorithm.recommend import RECOMMENDATION_MODES, recommend_meeting_stations  # noqa: E402

cases = {
    "강남권 편향 (강남x2, 역삼, 선릉, 혜화x1)": ["강남", "강남", "역삼", "선릉", "혜화"],
    "대칭 (신촌x2, 잠실x2)": ["신촌(지하)", "신촌(지하)", "잠실(송파구청)", "잠실(송파구청)"],
    "5인 분산 (혜화/강남/잠실/신촌/노량진)": ["혜화", "강남", "잠실(송파구청)", "신촌(지하)", "노량진"],
}

MODES = ["fair", "fast", "balanced"]


def print_case(name: str, origins: list[str]) -> None:
    print("=" * 70)
    print(f"CASE: {name}")
    print(f"Origins: {' / '.join(origins)}")
    print()

    for mode in MODES:
        weights = RECOMMENDATION_MODES[mode]
        results = recommend_meeting_stations(origins, top_k=3, mode=mode)

        print(f"--- mode: {mode} (w_mean={weights['w_mean']}, w_max={weights['w_max']}, "
              f"w_gap={weights['w_gap']}) ---")
        print(f"{'station':22s} {'score':>7s} {'mean':>7s} {'max':>7s} {'gap':>7s}")
        for r in results:
            print(
                f"{r['station']:22s} {r['score']:7.2f} {r['mean_time']:7.2f} "
                f"{r['max_time']:7.2f} {r['time_gap']:7.2f}"
            )
        print()

    fair_top1 = recommend_meeting_stations(origins, top_k=1, mode="fair")[0]["station"]
    fast_top1 = recommend_meeting_stations(origins, top_k=1, mode="fast")[0]["station"]
    balanced_top1 = recommend_meeting_stations(origins, top_k=1, mode="balanced")[0]["station"]
    print(
        f"1위 비교 -> fair: {fair_top1} / fast: {fast_top1} / balanced: {balanced_top1}"
        f"  ({'서로 다름' if len({fair_top1, fast_top1, balanced_top1}) > 1 else '동일'})"
    )
    print()


def main() -> None:
    for name, origins in cases.items():
        print_case(name, origins)


if __name__ == "__main__":
    main()