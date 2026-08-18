"""Kakao Local REST API 기반 장소 검색 클라이언트."""

import math
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
KAKAO_CATEGORY_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/category.json"
KAKAO_KEYWORD_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
RESTAURANT_CATEGORY_CODE = "FD6"
CAFE_CATEGORY_CODE = "CE7"
DEFAULT_TIMEOUT_SEC = 10


class KakaoLocalError(RuntimeError):
    """Kakao Local 설정 또는 API 호출이 실패했을 때 발생."""


def load_kakao_api_key(env_path: str | Path = ENV_PATH) -> str:
    """Kakao REST API 키를 읽는다.

    로컬 개발 환경에서는 프로젝트 .env 파일에서 읽고, 배포 환경(Render 등)처럼
    .env 파일 없이 환경변수가 프로세스에 직접 주입되는 경우에는 .env 로딩을
    건너뛰고 os.getenv로 바로 읽는다.
    """
    path = Path(env_path)
    if path.is_file():
        load_dotenv(dotenv_path=path, override=False)

    api_key = os.getenv("KAKAO_REST_API_KEY", "").strip()
    if not api_key:
        raise KakaoLocalError("KAKAO_REST_API_KEY가 설정되어 있지 않습니다.")
    return api_key


def _validate_search_options(
    latitude: float,
    longitude: float,
    radius_m: int,
    limit: int,
) -> None:
    if not math.isfinite(latitude) or not -90 <= latitude <= 90:
        raise ValueError(f"위도 값이 올바르지 않습니다: {latitude}")
    if not math.isfinite(longitude) or not -180 <= longitude <= 180:
        raise ValueError(f"경도 값이 올바르지 않습니다: {longitude}")
    if not 0 <= radius_m <= 20_000:
        raise ValueError("검색 반경은 0~20000m 사이여야 합니다.")
    if not 1 <= limit <= 15:
        raise ValueError("검색 결과 개수는 1~15 사이여야 합니다.")


def _error_detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return ""

    if not isinstance(payload, dict):
        return ""

    message = payload.get("msg") or payload.get("message")
    code = payload.get("code")
    if message and code is not None:
        return f"{message} (code: {code})"
    if message:
        return str(message)
    if code is not None:
        return f"code: {code}"
    return ""


def _raise_api_error(response: requests.Response) -> None:
    status = response.status_code
    guidance = {
        400: "요청 좌표, 검색어, 반경 또는 카테고리 값을 확인하세요.",
        401: "KAKAO_REST_API_KEY가 올바른지 확인하세요.",
        403: "Kakao 앱의 Local API 사용 설정과 권한을 확인하세요.",
        429: "Kakao Local API 호출 한도를 초과했습니다. 잠시 후 다시 시도하세요.",
    }.get(status)
    if guidance is None and status >= 500:
        guidance = "Kakao 서버 오류입니다. 잠시 후 다시 시도하세요."
    if guidance is None:
        guidance = "Kakao Local API 요청을 처리하지 못했습니다."

    detail = _error_detail(response)
    suffix = f" Kakao 응답: {detail}" if detail else ""
    raise KakaoLocalError(f"Kakao Local API 요청 실패 (HTTP {status}). {guidance}{suffix}")


def _number_or_none(value: Any, number_type: type[int] | type[float]) -> int | float | None:
    if value in (None, ""):
        return None
    try:
        return number_type(value)
    except (TypeError, ValueError):
        return None


def _text_or_empty(value: Any) -> str:
    return "" if value is None else str(value)


def _normalize_place(document: dict[str, Any]) -> dict[str, Any]:
    """Kakao 장소 응답을 서비스 공통 형식으로 바꾼다."""
    return {
        "id": _text_or_empty(document.get("id")),
        "name": _text_or_empty(document.get("place_name")),
        "category": _text_or_empty(document.get("category_name")),
        "distance_m": _number_or_none(document.get("distance"), int),
        "address": _text_or_empty(document.get("address_name")),
        "road_address": _text_or_empty(document.get("road_address_name")),
        "phone": _text_or_empty(document.get("phone")),
        "latitude": _number_or_none(document.get("y"), float),
        "longitude": _number_or_none(document.get("x"), float),
        "place_url": _text_or_empty(document.get("place_url")),
    }


def _distance_sort_key(place: dict[str, Any]) -> tuple[bool, int | float]:
    distance = place.get("distance_m")
    return distance is None, distance if isinstance(distance, (int, float)) else 0


def _request_places(
    *,
    url: str,
    api_key: str,
    params: dict[str, Any],
    limit: int,
    timeout_sec: int,
    session: Any | None,
) -> list[dict[str, Any]]:
    if not isinstance(api_key, str) or not api_key.strip():
        raise KakaoLocalError("KAKAO_REST_API_KEY가 비어 있습니다.")

    requester = session if session is not None else requests
    try:
        response = requester.get(
            url,
            headers={"Authorization": f"KakaoAK {api_key}"},
            params=params,
            timeout=timeout_sec,
        )
    except requests.Timeout as exc:
        raise KakaoLocalError(
            f"Kakao Local API 응답 시간이 {timeout_sec}초를 초과했습니다."
        ) from exc
    except requests.ConnectionError as exc:
        raise KakaoLocalError("Kakao Local API 서버에 연결할 수 없습니다.") from exc
    except requests.RequestException as exc:
        raise KakaoLocalError(
            f"Kakao Local API 요청 중 네트워크 오류가 발생했습니다: {exc}"
        ) from exc

    if not 200 <= response.status_code < 300:
        _raise_api_error(response)

    try:
        payload = response.json()
    except ValueError as exc:
        raise KakaoLocalError(
            "Kakao Local API가 올바른 JSON 응답을 반환하지 않았습니다."
        ) from exc

    documents = payload.get("documents") if isinstance(payload, dict) else None
    if not isinstance(documents, list):
        raise KakaoLocalError("Kakao Local API 응답에 documents 목록이 없습니다.")

    places = [_normalize_place(item) for item in documents if isinstance(item, dict)]
    places.sort(key=_distance_sort_key)
    return places[:limit]


def search_places_by_category(
    *,
    api_key: str,
    latitude: float,
    longitude: float,
    category_code: str,
    radius_m: int = 1_000,
    limit: int = 5,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    session: Any | None = None,
) -> list[dict[str, Any]]:
    """지정 좌표 주변 장소를 카테고리로 검색해 거리순으로 반환한다."""
    _validate_search_options(latitude, longitude, radius_m, limit)
    if not isinstance(category_code, str) or not category_code.strip():
        raise ValueError("카테고리 코드는 비어 있을 수 없습니다.")

    return _request_places(
        url=KAKAO_CATEGORY_SEARCH_URL,
        api_key=api_key,
        params={
            "category_group_code": category_code.strip(),
            "x": longitude,
            "y": latitude,
            "radius": radius_m,
            "size": limit,
            "sort": "distance",
        },
        limit=limit,
        timeout_sec=timeout_sec,
        session=session,
    )


def search_places_by_keyword(
    *,
    api_key: str,
    query: str,
    latitude: float,
    longitude: float,
    radius_m: int = 1_000,
    limit: int = 5,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    session: Any | None = None,
) -> list[dict[str, Any]]:
    """지정 좌표 주변 장소를 키워드로 검색해 거리순으로 반환한다."""
    _validate_search_options(latitude, longitude, radius_m, limit)
    if not isinstance(query, str) or not query.strip():
        raise ValueError("검색 키워드는 비어 있을 수 없습니다.")

    return _request_places(
        url=KAKAO_KEYWORD_SEARCH_URL,
        api_key=api_key,
        params={
            "query": query.strip(),
            "x": longitude,
            "y": latitude,
            "radius": radius_m,
            "size": limit,
            "sort": "distance",
        },
        limit=limit,
        timeout_sec=timeout_sec,
        session=session,
    )


def search_nearby_cafes(
    latitude: float,
    longitude: float,
    *,
    radius_m: int = 1_000,
    limit: int = 5,
    api_key: str | None = None,
    session: Any | None = None,
) -> list[dict[str, Any]]:
    """CE7 카테고리의 카페를 거리순으로 검색한다."""
    resolved_api_key = api_key if api_key is not None else load_kakao_api_key()
    cafes = search_places_by_category(
        api_key=resolved_api_key,
        latitude=latitude,
        longitude=longitude,
        category_code=CAFE_CATEGORY_CODE,
        radius_m=radius_m,
        limit=limit,
        session=session,
    )

    # 초기 카페 검색 코드의 주소 선택 방식과 url 키를 호환 목적으로 유지한다.
    return [
        {
            **cafe,
            "address": cafe["road_address"] or cafe["address"],
            "url": cafe["place_url"],
        }
        for cafe in cafes
    ]
