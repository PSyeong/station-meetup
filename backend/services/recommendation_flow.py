"""만남역 TOP 3와 선택 역의 장소 추천을 연결하는 애플리케이션 서비스."""

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from backend.algorithm.recommend import DEFAULT_MODE, recommend_meeting_stations
from backend.places.kakao_local import load_kakao_api_key
from backend.places.service import (
    DEFAULT_LIMIT,
    DEFAULT_RADIUS_M,
    SUPPORTED_CATEGORIES,
    recommend_places_near_station,
)
from backend.places.station_lookup import GRAPH_PATH


DEFAULT_TOP_K = 3


def recommend_meeting_options(
    origins: list[str],
    *,
    top_k: int = DEFAULT_TOP_K,
    mode: str = DEFAULT_MODE,
    weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """장소 API를 호출하지 않고 기존 알고리즘의 만남역 추천 결과를 반환한다."""
    return recommend_meeting_stations(
        origins,
        top_k=top_k,
        mode=mode,
        weights=weights,
    )


def recommend_places_for_selection(
    meeting_stations: list[dict[str, Any]],
    selected_index: int,
    *,
    categories: Iterable[str] = SUPPORTED_CATEGORIES,
    radius_m: int = DEFAULT_RADIUS_M,
    limit: int = DEFAULT_LIMIT,
    api_key: str | None = None,
    session: Any | None = None,
    graph_path: str | Path = GRAPH_PATH,
) -> dict[str, Any]:
    """추천 결과에서 선택된 역 한 곳에 대해서만 카테고리별 장소를 조회한다."""
    selected_recommendation = _select_recommendation(meeting_stations, selected_index)
    station_id = selected_recommendation.get("station")
    if not isinstance(station_id, str) or not station_id.strip():
        raise ValueError("선택한 추천 결과에 올바른 station 값이 없습니다.")

    requested_categories = _normalize_categories(categories)
    resolved_api_key = api_key if api_key is not None else load_kakao_api_key()

    places_by_category = {
        category: recommend_places_near_station(
            station_id,
            category,
            radius_m=radius_m,
            limit=limit,
            api_key=resolved_api_key,
            session=session,
            graph_path=graph_path,
        )
        for category in requested_categories
    }
    return {
        "selected_index": selected_index,
        "selected_station": station_id,
        "selected_recommendation": selected_recommendation,
        "places": places_by_category,
    }


def _select_recommendation(
    meeting_stations: list[dict[str, Any]], selected_index: int
) -> dict[str, Any]:
    if not meeting_stations:
        raise ValueError("선택할 추천역 결과가 없습니다.")
    if isinstance(selected_index, bool) or not isinstance(selected_index, int):
        raise ValueError("추천역 선택 인덱스는 정수여야 합니다.")
    if not 0 <= selected_index < len(meeting_stations):
        raise ValueError(
            f"추천역 선택 인덱스가 범위를 벗어났습니다: {selected_index} "
            f"(선택 가능: 0~{len(meeting_stations) - 1})"
        )

    selected = meeting_stations[selected_index]
    if not isinstance(selected, dict):
        raise ValueError("선택한 추천역 결과가 올바른 dict 형식이 아닙니다.")
    return selected


def _normalize_categories(categories: Iterable[str]) -> tuple[str, ...]:
    requested = (categories,) if isinstance(categories, str) else tuple(categories)
    requested = tuple(dict.fromkeys(requested))
    if not requested:
        raise ValueError("장소 카테고리는 최소 1개 이상이어야 합니다.")

    unsupported = [category for category in requested if category not in SUPPORTED_CATEGORIES]
    if unsupported:
        supported = ", ".join(SUPPORTED_CATEGORIES)
        raise ValueError(
            f"지원하지 않는 장소 카테고리입니다: {unsupported}. 지원값: {supported}"
        )
    return requested
