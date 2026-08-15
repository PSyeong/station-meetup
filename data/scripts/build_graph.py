"""
seoul_lines_normalized.json -> station_graph.json 그래프 빌드 스크립트
(normalize_seoul_lines.py의 캐시된 산출물만 읽는다. 원본 xlsx는 다시 열지 않는다.)

사용법:
    python data/scripts/build_graph.py

입력:
    data/processed/seoul_lines_normalized.json

출력:
    data/station_graph.json

역/거리/소요시간 계산 방식:
- 노드 id는 역사명(station_name)으로 통일한다. 환승역은 여러 노선 행(row)이
  같은 역사명으로 들어오므로 하나의 노드로 병합된다.
  (팀 공용 역명 표기 규칙: station_name 원본 표기를 그대로 사용)
- 같은 노선(line_name, 정규화된 값) 내에서 인접 구간으로 간주하고 엣지를 만든다.
  순서는 normalize_seoul_lines.py가 이미 실제 노선 순서로 정렬해 저장한 것을
  그대로 신뢰한다 (여기서 역번호로 재정렬하지 않음).
- SPUR_STATIONS(서동탄역/광명역)는 본선이 아니라 갈라지는 지선 종점이라 본선
  시퀀스에서 빼고, EXTRA_EDGES로 실제 분기역과 직접 연결한다. 2호선 신정지선
  (도림천-양천구청-신정네거리)은 본선 순서상 붙어있지만 신도림역과의 연결이
  빠져 있어 EXTRA_EDGES로 보강한다.
- 인접역 간 하버사인 거리(km) -> 표정속도(정차시간 포함) 나눠 소요시간(분) 추정.
- 환승역을 지나는 구간에는 고정 페널티를 더한다.
"""

import json
import math
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parents[1] / "processed"
INPUT_PATH = PROCESSED_DIR / "seoul_lines_normalized.json"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "station_graph.json"

# 지하철 표정속도(정차시간 포함, km/h). 팀 협의로 32~35 범위에서 조정 가능.
AVG_SPEED_KMH = 33
# 환승역 통과 시 고정 페널티(분)
TRANSFER_PENALTY_MIN = 4.5

# 본선 시퀀스에서 제외하고 아래 EXTRA_EDGES로 직접 연결하는 지선 역.
# normalize_seoul_lines.py의 MANUAL_LINE_ORDER/SPUR_STATIONS와 짝을 이룬다.
# - 서동탄역/광명역: 경부선에서 갈라지는 지선 종점
# - 도림천/양천구청/신정네거리: 2호선 신정지선 (신도림에서 분기)
# - 용답/신답/용두(동대문구청): 2호선 성수지선 (성수~신설동을 잇는 지선)
# - 신설동: 2호선 순환 본선에는 없고 성수지선의 반대쪽 끝점 역할만 함
# 이 역들은 station_id가 본선과 섞여 있어 그대로 두면 station_id 순서상
# 엉뚱한 본선 역과 인접한 것처럼 연결된다. 단, 신설동은 1호선 본선 시퀀스에는
# 그대로 포함되어야 하므로(1호선 환승역), 2호선 쪽 시퀀스에서만 제외되도록
# build_edges에서 line 단위로 처리한다.
SPUR_STATIONS = {
    "서동탄역", "광명역",
    "도림천", "양천구청", "신정네거리",
    "용답", "신답", "용두(동대문구청)",
}
SPUR_STATIONS_BY_LINE = {
    "2호선": {"신설동"},
}

# 본선 시퀀스만으로는 만들어지지 않는 분기/지선 연결을 직접 추가한다.
# (담당1 수동 검증, 2026-08-15)
EXTRA_EDGES = [
    # 세 번째 값은 정규화된 노선명("1호선")을 쓴다. 원본 세부 노선명(경부선/경인선)을
    # 그대로 쓰면 프론트엔드가 모르는 라벨이라 어떤 노선을 켜도 렌더링되지 않는다.
    ("병점역", "서동탄역", "1호선"),   # 병점역에서 갈라지는 서동탄지선 (원본: 경부선)
    ("금천구청역", "광명역", "1호선"),  # 금천구청역에서 갈라지는 광명역 셔틀 지선 (원본: 경부선)
    ("구로역", "구일역", "1호선"),     # 구로역에서 갈라지는 경인선 분기 시작점 (원본: 경인선)
    ("신도림", "도림천", "2호선"),      # 신정지선: 신도림-도림천-양천구청-신정네거리
    ("도림천", "양천구청", "2호선"),
    ("양천구청", "신정네거리", "2호선"),
    ("성수", "용답", "2호선"),         # 성수지선: 성수-용답-신답-용두-신설동
    ("용답", "신답", "2호선"),
    ("신답", "용두(동대문구청)", "2호선"),
    ("용두(동대문구청)", "신설동", "2호선"),
]

# 1호선은 경원선/1호선/경부선/경인선 4개 원본 구간을 이어붙여 만든 것이라, 구간이
# 바뀌는 경계에서 실제로는 인접하지 않은 역끼리 연결될 수 있다. 경부선(남영~천안)
# 끝에서 경인선(구일~인천) 시작으로 넘어가는 지점이 대표적 - 둘 다 구로역에서
# 갈라지는 별개 지선이라 순서상 이어붙이면 안 된다(위 EXTRA_EDGES의 구로-구일
# 연결로 대신한다).
# 경원선(소요산~청량리) 끝에서 1호선(청량리~서울역) 시작으로 넘어가는 지점은 두
# 구간이 청량리역에서 실제로 만나므로(자기 자신과의 쌍은 build_edges에서 자동
# 스킵됨) 별도 처리가 필요 없다.
# (담당1 수동 검증, 2026-08-15)
INVALID_SEGMENT_TRANSITIONS = {
    ("경부선", "경인선"),
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def load_records() -> list[dict]:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"{INPUT_PATH}가 없습니다. 먼저 normalize_seoul_lines.py를 실행하세요."
        )
    return json.loads(INPUT_PATH.read_text(encoding="utf-8"))


def build_nodes(records: list[dict]) -> dict[str, dict]:
    nodes: dict[str, dict] = {}
    for rec in records:
        name = rec["station_name"]
        node = nodes.setdefault(
            name,
            {
                "id": name,
                "name": name,
                "name_en": rec["name_en"],
                "lat": float(rec["lat"]),
                "lng": float(rec["lng"]),
                "lines": [],
                "is_transfer": False,
            },
        )
        if rec["line_name"] not in node["lines"]:
            node["lines"].append(rec["line_name"])
        node["is_transfer"] = node["is_transfer"] or bool(rec["is_transfer"]) or len(node["lines"]) > 1
    return nodes


def _make_edge_pair(na: dict, nb: dict, line: str) -> list[dict]:
    distance_km = haversine_km(na["lat"], na["lng"], nb["lat"], nb["lng"])
    time_min = (distance_km / AVG_SPEED_KMH) * 60
    if na["is_transfer"] or nb["is_transfer"]:
        time_min += TRANSFER_PENALTY_MIN

    return [
        {
            "from": src,
            "to": dst,
            "line": line,
            "distance_km": round(distance_km, 3),
            "time_min": round(time_min, 2),
        }
        for src, dst in ((na["id"], nb["id"]), (nb["id"], na["id"]))
    ]


def build_edges(records: list[dict], nodes: dict[str, dict]) -> list[dict]:
    by_line: dict[str, list[dict]] = {}
    for rec in records:
        if rec["station_name"] in SPUR_STATIONS:
            continue  # 본선 시퀀스에서 제외, EXTRA_EDGES로 별도 연결
        if rec["station_name"] in SPUR_STATIONS_BY_LINE.get(rec["line_name"], ()):
            continue  # 해당 노선 시퀀스에서만 제외 (다른 노선에서는 정상 포함)
        by_line.setdefault(rec["line_name"], []).append(rec)

    edges = []
    for line, recs in by_line.items():
        # recs는 records 순회 순서를 그대로 유지하므로, normalize_seoul_lines.py가
        # 정렬해둔 실제 노선 순서가 보존된다.
        for a, b in zip(recs, recs[1:]):
            na, nb = nodes[a["station_name"]], nodes[b["station_name"]]
            if na["id"] == nb["id"]:
                continue
            if (a["line_name_raw"], b["line_name_raw"]) in INVALID_SEGMENT_TRANSITIONS:
                continue
            edges.extend(_make_edge_pair(na, nb, line))

    for name_a, name_b, line in EXTRA_EDGES:
        edges.extend(_make_edge_pair(nodes[name_a], nodes[name_b], line))

    return edges


def main() -> None:
    records = load_records()
    nodes = build_nodes(records)
    edges = build_edges(records, nodes)

    graph = {
        "meta": {
            "source": "seoul_lines_normalized.json",
            "avg_speed_kmh": AVG_SPEED_KMH,
            "transfer_penalty_min": TRANSFER_PENALTY_MIN,
            "station_count": len(nodes),
            "edge_count": len(edges),
        },
        "nodes": list(nodes.values()),
        "edges": edges,
    }

    OUTPUT_PATH.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(nodes)}개 역, {len(edges)}개 엣지 -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
