"""backend/algorithm/recommend.py, backend/places/service.py를 HTTP로 노출하는 FastAPI 서버.

실행(레포 루트에서): uvicorn backend.api.main:app --reload --port 8000
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.algorithm.recommend import recommend_meeting_stations
from backend.algorithm.shortest_path import NoPathFoundError, StationNotFoundError
from backend.api.schemas import (
    HealthResponse,
    PlacesRequest,
    PlacesResponse,
    RecommendationItem,
    RecommendationRequest,
)
from backend.places.kakao_local import KakaoLocalError
from backend.places.service import recommend_places_near_station
from backend.places.station_lookup import StationLookupError


DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://localhost:5183"


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(title="station-meetup API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StationNotFoundError)
@app.exception_handler(NoPathFoundError)
@app.exception_handler(StationLookupError)
@app.exception_handler(ValueError)
def _handle_bad_request(_request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(KakaoLocalError)
def _handle_kakao_error(_request, exc: KakaoLocalError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/api/recommendations", response_model=list[RecommendationItem])
def recommendations(payload: RecommendationRequest) -> list[dict]:
    return recommend_meeting_stations(payload.origins, top_k=payload.top_k, mode=payload.mode)


@app.post("/api/places", response_model=PlacesResponse)
def places(payload: PlacesRequest) -> PlacesResponse:
    places_by_category = {
        category: recommend_places_near_station(
            payload.station_id,
            category,
            radius_m=payload.radius_m,
            limit=payload.limit,
        )
        for category in payload.categories
    }
    return PlacesResponse(station_id=payload.station_id, places=places_by_category)
