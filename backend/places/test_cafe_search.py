"""강남역 주변 카페 검색을 터미널에서 확인하는 실호출 테스트.

실행:
    python backend/places/test_cafe_search.py
"""

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.places.kakao_local import KakaoLocalError, search_nearby_cafes  # noqa: E402
from backend.places.station_lookup import StationLookupError, get_station_location  # noqa: E402


STATION_ID = "강남"
RADIUS_M = 1_000
LIMIT = 5


def _print_place(index: int, place: dict) -> None:
    distance = place["distance_m"]
    distance_text = f"{distance}m" if distance is not None else "거리 정보 없음"

    print(f"{index}. {place['name']} ({distance_text})")
    print(f"   주소: {place['address'] or '주소 정보 없음'}")
    if place["phone"]:
        print(f"   전화: {place['phone']}")
    if place["url"]:
        print(f"   Kakao Map: {place['url']}")


def main() -> int:
    try:
        station = get_station_location(STATION_ID)
        cafes = search_nearby_cafes(
            latitude=float(station["lat"]),
            longitude=float(station["lng"]),
            radius_m=RADIUS_M,
            limit=LIMIT,
        )
    except (StationLookupError, KakaoLocalError, ValueError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    print("강남역 주변 카페 검색 결과")
    print(f"기준 좌표: 위도 {station['lat']}, 경도 {station['lng']}")
    print(f"검색 조건: 반경 {RADIUS_M}m / 거리순 / 최대 {LIMIT}개")
    print()

    if not cafes:
        print("조건에 맞는 카페를 찾지 못했습니다.")
        return 0

    for index, cafe in enumerate(cafes, start=1):
        _print_place(index, cafe)
        if index != len(cafes):
            print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
