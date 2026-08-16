"""station_graph.json에서 장소 검색에 필요한 역 좌표를 조회한다."""

import json
import math
from pathlib import Path


GRAPH_PATH = Path(__file__).resolve().parents[2] / "data" / "station_graph.json"


class StationLookupError(RuntimeError):
    """역 데이터 파일을 읽거나 요청한 역을 찾을 수 없을 때 발생."""


def get_station_location(
    station_id: str, graph_path: str | Path = GRAPH_PATH
) -> dict[str, str | float]:
    """그래프 노드 id와 정확히 일치하는 역의 이름과 위도/경도를 반환한다."""
    path = Path(graph_path)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StationLookupError(f"지하철 그래프 파일을 찾을 수 없습니다: {path}") from exc
    except json.JSONDecodeError as exc:
        raise StationLookupError(f"지하철 그래프 파일이 올바른 JSON이 아닙니다: {path}") from exc
    except OSError as exc:
        raise StationLookupError(f"지하철 그래프 파일을 읽을 수 없습니다: {path}") from exc

    nodes = data.get("nodes") if isinstance(data, dict) else None
    if not isinstance(nodes, list):
        raise StationLookupError("지하철 그래프에 nodes 목록이 없습니다.")

    node = next(
        (item for item in nodes if isinstance(item, dict) and item.get("id") == station_id),
        None,
    )
    if node is None:
        raise StationLookupError(f"지하철 그래프에서 역을 찾을 수 없습니다: {station_id}")

    try:
        latitude = float(node["lat"])
        longitude = float(node["lng"])
    except (KeyError, TypeError, ValueError) as exc:
        raise StationLookupError(f"{station_id} 역의 위도/경도 값이 올바르지 않습니다.") from exc

    if not math.isfinite(latitude) or not -90 <= latitude <= 90:
        raise StationLookupError(f"{station_id} 역의 위도 값이 범위를 벗어났습니다: {latitude}")
    if not math.isfinite(longitude) or not -180 <= longitude <= 180:
        raise StationLookupError(f"{station_id} 역의 경도 값이 범위를 벗어났습니다: {longitude}")

    return {
        "id": station_id,
        "name": str(node.get("name", station_id)),
        "lat": latitude,
        "lng": longitude,
    }
