"""backend/api 엔드포인트의 요청/응답 Pydantic 모델.

recommend_meeting_stations()/recommend_places_near_station()의 반환 dict shape을
그대로 반영한다 - 프론트 mockRecommendation.js/mockPlaces.js와 필드명을 맞추기 위함.
"""

from typing import Literal

from pydantic import BaseModel, Field

from backend.places.service import SUPPORTED_CATEGORIES


RecommendationMode = Literal["fair", "fast", "balanced"]
PlaceCategory = Literal["맛집", "카페", "놀거리"]


class RecommendationRequest(BaseModel):
    origins: list[str] = Field(min_length=1)
    mode: RecommendationMode = "balanced"
    top_k: int = Field(default=3, ge=1)


class TravelTime(BaseModel):
    origin: str
    time: float


class RecommendationItem(BaseModel):
    station: str
    score: float
    mean_time: float
    max_time: float
    min_time: float
    time_gap: float
    std_time: float
    travel_times: list[TravelTime]
    longest_travel: TravelTime
    shortest_travel: TravelTime


class PlacesRequest(BaseModel):
    station_id: str
    categories: list[PlaceCategory] = Field(default_factory=lambda: list(SUPPORTED_CATEGORIES))
    radius_m: int = Field(default=1_000, gt=0)
    limit: int = Field(default=5, ge=1, le=5)


class Place(BaseModel):
    id: str
    name: str
    category: str
    distance_m: int | None
    address: str
    road_address: str
    phone: str
    latitude: float | None
    longitude: float | None
    place_url: str


class PlacesResponse(BaseModel):
    station_id: str
    places: dict[str, list[Place]]


class HealthResponse(BaseModel):
    status: str = "ok"
