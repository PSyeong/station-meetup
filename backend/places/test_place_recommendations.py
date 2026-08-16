r"""강남역 주변 맛집, 카페, 놀거리 추천을 실제 API로 확인한다.

실행:
    .\.venv\Scripts\python.exe backend\places\test_place_recommendations.py
"""

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.places.kakao_local import KakaoLocalError, load_kakao_api_key  # noqa: E402
from backend.places.service import (  # noqa: E402
    DEFAULT_LIMIT,
    DEFAULT_RADIUS_M,
    SUPPORTED_CATEGORIES,
    recommend_places_by_location,
)
from backend.places.station_lookup import StationLookupError, get_station_location  # noqa: E402


STATION_ID = "강남"


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
        station = get_station_location(STATION_ID)
        api_key = load_kakao_api_key()
        recommendations = {
            category: recommend_places_by_location(
                category,
                latitude=float(station["lat"]),
                longitude=float(station["lng"]),
                radius_m=DEFAULT_RADIUS_M,
                limit=DEFAULT_LIMIT,
                api_key=api_key,
            )
            for category in SUPPORTED_CATEGORIES
        }
    except (StationLookupError, KakaoLocalError, ValueError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    print(f"{station['name']}역 주변 장소 추천")
    print(f"기준 좌표: 위도 {station['lat']}, 경도 {station['lng']}")
    print(f"검색 조건: 반경 {DEFAULT_RADIUS_M}m / 거리순 / 카테고리별 최대 {DEFAULT_LIMIT}개")

    for category, places in recommendations.items():
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
