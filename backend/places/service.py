"""역 주변 맛집, 카페, 놀거리 추천 서비스."""

from pathlib import Path
from typing import Any

from backend.places.kakao_local import (
    CAFE_CATEGORY_CODE,
    RESTAURANT_CATEGORY_CODE,
    KakaoLocalError,
    load_kakao_api_key,
    search_places_by_category,
    search_places_by_keyword,
)
from backend.places.station_lookup import GRAPH_PATH, get_station_location


DEFAULT_RADIUS_M = 1_000
DEFAULT_LIMIT = 5
KEYWORD_FETCH_LIMIT = 15
CATEGORY_CODES = {
    "맛집": RESTAURANT_CATEGORY_CODE,
    "카페": CAFE_CATEGORY_CODE,
}
ENTERTAINMENT_CATEGORY = "놀거리"
ENTERTAINMENT_KEYWORDS = (
    "방탈출",
    "보드게임카페",
    "볼링장",
    "영화관",
    "전시",
)
SUPPORTED_CATEGORIES = (*CATEGORY_CODES, ENTERTAINMENT_CATEGORY)


def recommend_places_by_location(
    category: str,
    latitude: float,
    longitude: float,
    *,
    radius_m: int = DEFAULT_RADIUS_M,
    limit: int = DEFAULT_LIMIT,
    api_key: str | None = None,
    session: Any | None = None,
) -> list[dict[str, Any]]:
    """좌표와 서비스 카테고리를 기준으로 장소를 추천한다."""
    normalized_category = category.strip() if isinstance(category, str) else ""
    if normalized_category not in SUPPORTED_CATEGORIES:
        supported = ", ".join(SUPPORTED_CATEGORIES)
        raise ValueError(f"지원하지 않는 장소 카테고리입니다: {category}. 지원값: {supported}")
    if not 1 <= limit <= DEFAULT_LIMIT:
        raise ValueError(f"추천 결과 개수는 1~{DEFAULT_LIMIT} 사이여야 합니다.")

    resolved_api_key = api_key if api_key is not None else load_kakao_api_key()
    category_code = CATEGORY_CODES.get(normalized_category)
    if category_code is not None:
        return search_places_by_category(
            api_key=resolved_api_key,
            latitude=latitude,
            longitude=longitude,
            category_code=category_code,
            radius_m=radius_m,
            limit=limit,
            session=session,
        )

    return _search_entertainment_places(
        api_key=resolved_api_key,
        latitude=latitude,
        longitude=longitude,
        radius_m=radius_m,
        limit=limit,
        session=session,
    )


def recommend_places_near_station(
    station_id: str,
    category: str,
    *,
    radius_m: int = DEFAULT_RADIUS_M,
    limit: int = DEFAULT_LIMIT,
    api_key: str | None = None,
    session: Any | None = None,
    graph_path: str | Path = GRAPH_PATH,
) -> list[dict[str, Any]]:
    """station_graph.json의 역 좌표를 기준으로 장소를 추천한다."""
    station = get_station_location(station_id, graph_path=graph_path)
    return recommend_places_by_location(
        category,
        latitude=float(station["lat"]),
        longitude=float(station["lng"]),
        radius_m=radius_m,
        limit=limit,
        api_key=api_key,
        session=session,
    )


def _search_entertainment_places(
    *,
    api_key: str,
    latitude: float,
    longitude: float,
    radius_m: int,
    limit: int,
    session: Any | None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for keyword in ENTERTAINMENT_KEYWORDS:
        try:
            places = search_places_by_keyword(
                api_key=api_key,
                query=keyword,
                latitude=latitude,
                longitude=longitude,
                radius_m=radius_m,
                limit=KEYWORD_FETCH_LIMIT,
                session=session,
            )
        except KakaoLocalError as exc:
            raise KakaoLocalError(f"'{keyword}' 놀거리 검색에 실패했습니다. {exc}") from exc
        candidates.extend(places)

    candidates.sort(key=_place_sort_key)

    unique_places: dict[tuple[Any, ...], dict[str, Any]] = {}
    for place in candidates:
        unique_places.setdefault(_deduplication_key(place), place)
    return list(unique_places.values())[:limit]


def _place_sort_key(place: dict[str, Any]) -> tuple[bool, int | float, str]:
    distance = place.get("distance_m")
    return (
        distance is None,
        distance if isinstance(distance, (int, float)) else 0,
        str(place.get("name", "")),
    )


def _deduplication_key(place: dict[str, Any]) -> tuple[Any, ...]:
    place_id = place.get("id")
    if place_id:
        return "id", str(place_id)

    place_url = place.get("place_url")
    if place_url:
        return "place_url", str(place_url)

    return (
        "location",
        place.get("name"),
        place.get("latitude"),
        place.get("longitude"),
    )
