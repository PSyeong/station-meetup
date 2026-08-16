"""Kakao Local REST API의 카테고리 기반 장소 검색 클라이언트."""

import math
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
KAKAO_CATEGORY_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/category.json"
CAFE_CATEGORY_CODE = "CE7"
DEFAULT_TIMEOUT_SEC = 10


class KakaoLocalError(RuntimeError):
    """Kakao Local 설정 또는 API 호출이 실패했을 때 발생."""


def load_kakao_api_key(env_path: str | Path = ENV_PATH) -> str:
    """프로젝트 .env에서 Kakao REST API 키를 읽는다."""
    path = Path(env_path)
    if not path.is_file():
        raise KakaoLocalError(f".env 파일을 찾을 수 없습니다: {path}")

    load_dotenv(dotenv_path=path, override=False)
    api_key = os.getenv("KAKAO_REST_API_KEY", "").strip()
    if not api_key:
        raise KakaoLocalError(".env에 KAKAO_REST_API_KEY가 설정되어 있지 않습니다.")
    return api_key


def _validate_search_options(
    latitude: float,
    longitude: float,
    category_code: str,
    radius_m: int,
    limit: int,
) -> None:
    if not math.isfinite(latitude) or not -90 <= latitude <= 90:
        raise ValueError(f"위도 값이 올바르지 않습니다: {latitude}")
    if not math.isfinite(longitude) or not -180 <= longitude <= 180:
        raise ValueError(f"경도 값이 올바르지 않습니다: {longitude}")
    if not category_code:
        raise ValueError("카테고리 코드는 비어 있을 수 없습니다.")
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
        400: "요청 좌표, 반경, 카테고리 값을 확인하세요.",
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


def _normalize_place(document: dict[str, Any]) -> dict[str, Any]:
    """Kakao 응답 한 건을 화면과 테스트에서 쓰기 쉬운 형식으로 바꾼다."""
    road_address = str(document.get("road_address_name", ""))
    address = road_address or str(document.get("address_name", ""))
    return {
        "id": str(document.get("id", "")),
        "name": str(document.get("place_name", "")),
        "category": str(document.get("category_name", "")),
        "address": address,
        "phone": str(document.get("phone", "")),
        "distance_m": _number_or_none(document.get("distance"), int),
        "latitude": _number_or_none(document.get("y"), float),
        "longitude": _number_or_none(document.get("x"), float),
        "url": str(document.get("place_url", "")),
    }


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
    _validate_search_options(latitude, longitude, category_code, radius_m, limit)
    if not api_key.strip():
        raise KakaoLocalError("KAKAO_REST_API_KEY가 비어 있습니다.")

    requester = session or requests
    try:
        response = requester.get(
            KAKAO_CATEGORY_SEARCH_URL,
            headers={"Authorization": f"KakaoAK {api_key}"},
            params={
                "category_group_code": category_code,
                "x": longitude,
                "y": latitude,
                "radius": radius_m,
                "size": limit,
                "sort": "distance",
            },
            timeout=timeout_sec,
        )
    except requests.Timeout as exc:
        raise KakaoLocalError(
            f"Kakao Local API 응답 시간이 {timeout_sec}초를 초과했습니다."
        ) from exc
    except requests.ConnectionError as exc:
        raise KakaoLocalError("Kakao Local API 서버에 연결할 수 없습니다.") from exc
    except requests.RequestException as exc:
        raise KakaoLocalError(f"Kakao Local API 요청 중 네트워크 오류가 발생했습니다: {exc}") from exc

    if not 200 <= response.status_code < 300:
        _raise_api_error(response)

    try:
        payload = response.json()
    except ValueError as exc:
        raise KakaoLocalError("Kakao Local API가 올바른 JSON 응답을 반환하지 않았습니다.") from exc

    documents = payload.get("documents") if isinstance(payload, dict) else None
    if not isinstance(documents, list):
        raise KakaoLocalError("Kakao Local API 응답에 documents 목록이 없습니다.")

    places = [_normalize_place(item) for item in documents if isinstance(item, dict)]
    places.sort(
        key=lambda place: (
            place["distance_m"] is None,
            place["distance_m"] if place["distance_m"] is not None else 0,
        )
    )
    return places[:limit]


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
    return search_places_by_category(
        api_key=resolved_api_key,
        latitude=latitude,
        longitude=longitude,
        category_code=CAFE_CATEGORY_CODE,
        radius_m=radius_m,
        limit=limit,
        session=session,
    )
