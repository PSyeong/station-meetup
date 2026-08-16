r"""출발역 추천부터 선택 역 장소 조회까지 실제 데이터와 API로 확인한다.

실행:
    .\.venv\Scripts\python.exe backend\services\test_recommendation_flow.py
"""

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.algorithm.shortest_path import StationNotFoundError  # noqa: E402
from backend.places.kakao_local import KakaoLocalError  # noqa: E402
from backend.places.service import DEFAULT_LIMIT  # noqa: E402
from backend.places.station_lookup import StationLookupError  # noqa: E402
from backend.services.recommendation_flow import (  # noqa: E402
    DEFAULT_TOP_K,
    recommend_meeting_options,
    recommend_places_for_selection,
)


ORIGINS = ["혜화", "강남", "신촌(지하)"]
SELECTED_INDEX = 0


def _print_meeting_station(index: int, recommendation: dict) -> None:
    print(
        f"{index}. {recommendation['station']} "
        f"(점수 {recommendation['score']}, 평균 {recommendation['mean_time']}분, "
        f"최대 {recommendation['max_time']}분)"
    )


def _print_place(index: int, place: dict) -> None:
    distance = place["distance_m"]
    distance_text = f"{distance}m" if distance is not None else "거리 정보 없음"
    address = place["road_address"] or place["address"] or "주소 정보 없음"

    print(f"{index}. {place['name']} ({distance_text})")
    print(f"   카테고리: {place['category'] or '카테고리 정보 없음'}")
    print(f"   주소: {address}")
    if place["phone"]:
        print(f"   전화: {place['phone']}")
    if place["place_url"]:
        print(f"   Kakao Map: {place['place_url']}")


def main() -> int:
    try:
        meeting_stations = recommend_meeting_options(ORIGINS, top_k=DEFAULT_TOP_K)
    except (StationNotFoundError, ValueError) as exc:
        print(f"추천역 계산 오류: {exc}", file=sys.stderr)
        return 1

    if not meeting_stations:
        print("추천역 계산 결과가 없습니다.", file=sys.stderr)
        return 1

    print(f"출발역: {', '.join(ORIGINS)}")
    print(f"\n추천 만남역 TOP {len(meeting_stations)}")
    for index, recommendation in enumerate(meeting_stations, start=1):
        _print_meeting_station(index, recommendation)

    selected_station = meeting_stations[SELECTED_INDEX]["station"]
    print(f"\n선택역: {selected_station} ({SELECTED_INDEX + 1}번 추천)")

    try:
        selection = recommend_places_for_selection(
            meeting_stations,
            SELECTED_INDEX,
        )
    except (KakaoLocalError, StationLookupError, ValueError) as exc:
        print(f"장소 추천 오류: {exc}", file=sys.stderr)
        return 1

    if selection["selected_station"] != selected_station:
        print("장소 추천에 전달된 역이 선택역과 일치하지 않습니다.", file=sys.stderr)
        return 1

    unexpected_counts = {
        category: len(places)
        for category, places in selection["places"].items()
        if len(places) != DEFAULT_LIMIT
    }
    if unexpected_counts:
        print(
            f"카테고리별 {DEFAULT_LIMIT}개 장소를 받지 못했습니다: {unexpected_counts}",
            file=sys.stderr,
        )
        return 1

    for category, places in selection["places"].items():
        print(f"\n[{category}] {len(places)}개")
        if not places:
            print("조건에 맞는 장소를 찾지 못했습니다.")
            continue

        for index, place in enumerate(places, start=1):
            _print_place(index, place)
            if index != len(places):
                print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
