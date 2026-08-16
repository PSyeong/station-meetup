"""
recommend_meeting_stations()가 다양한 사용자 수/지리적 분포에서도 합리적으로
동작하는지 확인하기 위한 분석 스크립트.

기존 알고리즘(backend/algorithm/recommend.py, candidate_evaluation.py,
shortest_path.py)은 전혀 수정하지 않는다. 다양한 입력 케이스에 대해
recommend_meeting_stations()를 그대로 호출해 Top-5 결과를 출력하고,
결과의 논리적 타당성을 간단히 assert로 확인만 한다.

주의: 아래 cases의 일부 역명은 station_graph.json에 그 이름 그대로 존재하지
않아, 가장 근접한 실제 id로 교체했다.
  - "잠실"       -> "잠실(송파구청)"      (2호선/8호선 환승역, 실제 잠실역.
                                           "잠실나루"/"잠실새내"는 인접한 별개 역)
  - "성신여대입구" -> "성신여대입구(돈암)"  (4호선, 실제 성신여대입구역)
  - "삼성"       -> "삼성(무역센터)"      (2호선, 실제 삼성역.
                                           "삼성중앙"은 9호선의 다른 역이라 제외)

실행:
    python backend/algorithm/analyze_recommendations.py
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.algorithm.recommend import recommend_meeting_stations  # noqa: E402

cases = {
    "2인_혜화_강남": ["혜화", "강남"],
    "2인_강남_잠실": ["강남", "잠실(송파구청)"],
    "2인_신촌_건대": ["신촌(지하)", "건대입구"],
    "3인_기본": ["혜화", "강남", "신촌(지하)"],
    "3인_동남권": ["강남", "잠실(송파구청)", "건대입구"],
    "3인_북부권": ["혜화", "동대문", "성신여대입구(돈암)"],
    "4인_일반": ["혜화", "강남", "잠실(송파구청)", "신촌(지하)"],
    "4인_분산": ["혜화", "노량진", "강남", "건대입구"],
    "4인_강남권": ["강남", "역삼", "선릉", "잠실(송파구청)"],
    "5인_일반": ["혜화", "강남", "신촌(지하)", "잠실(송파구청)", "노량진"],
    "5인_지역편향": ["강남", "역삼", "선릉", "삼성(무역센터)", "잠실(송파구청)"],
    "6인_분산": ["혜화", "강남", "잠실(송파구청)", "신촌(지하)", "노량진", "건대입구"],
    "중복_혜화2_강남1": ["혜화", "혜화", "강남"],
    "중복_강남3_혜화1": ["강남", "강남", "강남", "혜화"],
    "대칭_신촌2_잠실2": ["신촌(지하)", "신촌(지하)", "잠실(송파구청)", "잠실(송파구청)"],
    "전원_강남": ["강남", "강남", "강남"],
    "한명_혜화": ["혜화"],
    "편향_강남권3_혜화1": ["강남", "역삼", "선릉", "혜화"],
    "편향_강남권4_혜화1": ["강남", "강남", "역삼", "선릉", "혜화"],
}


def print_case(name: str, origins: list[str]) -> list[dict]:
    print("=" * 60)
    print(f"CASE: {name}")
    print(f"Origins: {' / '.join(origins)}")
    print(f"인원 수: {len(origins)}")
    print()

    results = recommend_meeting_stations(origins, top_k=5)

    for rank, r in enumerate(results, start=1):
        print(f"{rank}. {r['station']}")
        print(f"   score: {r['score']}")
        print(f"   mean: {r['mean_time']}")
        print(f"   max: {r['max_time']}")
        print(f"   gap: {r['time_gap']}")
        print(f"   std: {r['std_time']}")
        if rank == 1:
            print()
            print("   individual:")
            for t in r["travel_times"]:
                print(f"   {t['origin']}: {t['time']}")
        print()

    return results


def main() -> None:
    all_results = {}
    for name, origins in cases.items():
        all_results[name] = print_case(name, origins)

    print("=" * 60)
    print("SANITY CHECKS")
    print("=" * 60)

    # 1. 전원 강남 -> 강남이 1위, score 0
    r = all_results["전원_강남"][0]
    print(f"[전원_강남] 1위: {r['station']} (기대: 강남), score: {r['score']} (기대: 0.0)")
    assert r["station"] == "강남"
    assert r["score"] == 0.0

    # 2. 혜화 2명 -> 혜화가 1위, score 0
    r2 = recommend_meeting_stations(["혜화", "혜화"], top_k=1)[0]
    print(f"[혜화_혜화] 1위: {r2['station']} (기대: 혜화), score: {r2['score']} (기대: 0.0)")
    assert r2["station"] == "혜화"
    assert r2["score"] == 0.0

    # 3. 동일 출발역 중복이 실제 인원수만큼 반영되는지
    dup = all_results["중복_강남3_혜화1"][0]
    origins_in_result = [t["origin"] for t in dup["travel_times"]]
    print(
        f"[중복_강남3_혜화1] 1위({dup['station']}) travel_times 인원: {len(dup['travel_times'])}명"
        f" (강남 {origins_in_result.count('강남')}명, 혜화 {origins_in_result.count('혜화')}명)"
    )
    assert len(dup["travel_times"]) == 4
    assert origins_in_result.count("강남") == 3
    assert origins_in_result.count("혜화") == 1

    # 4. 강남권 편향 정도에 따라 추천역이 어떻게 이동하는지 (assert 없이 비교만)
    biased3 = all_results["편향_강남권3_혜화1"][0]
    biased4 = all_results["편향_강남권4_혜화1"][0]
    print(f"[편향_강남권3_혜화1] 1위: {biased3['station']} (강남/역삼/선릉/혜화, 강남권 3:1)")
    print(f"[편향_강남권4_혜화1] 1위: {biased4['station']} (강남/강남/역삼/선릉/혜화, 강남권 4:1)")

    print()
    print("모든 sanity check 통과.")


if __name__ == "__main__":
    main()