"""
서울 도시철도(1~9호선 + 신분당선) 데이터 정규화 스크립트
원본: 전국도시철도역사정보표준데이터 (xlsx, data.go.kr)

원본 xlsx 파싱은 무거우므로 이 스크립트는 필요할 때만 수동 실행하고,
결과(data/processed/seoul_lines_normalized.*)를 캐시로 재사용한다.
build_graph.py는 이 캐시만 읽는다.

사용법:
    python data/scripts/normalize_seoul_lines.py

입력:
    data/raw/*.xlsx  (전국도시철도역사정보표준데이터 원본. 파일명의 날짜는 배포 시점마다 다를 수 있음)

출력:
    data/processed/seoul_lines_normalized.json
    data/processed/seoul_lines_normalized.csv

[1호선 처리 방침 - 완전한 실제 1호선 포함으로 확정]
실제 1호선 서비스는 데이터상 4개의 서로 다른 '노선명'으로 분리 저장되어 있음:
  - '1호선'  : 도심 구간 (서울역~청량리), 서울교통공사 운영, 10개역
  - '경원선' : 북쪽 연장 (청량리~소요산), 한국철도공사 운영
               단, 소요산 이후(청산/전곡/연천)는 지하철 서비스 구간이 아니므로 제외
  - '경부선' : 남쪽 연장 (~천안, 서동탄/광명 지선 포함), 한국철도공사 운영
  - '경인선' : 서쪽 연장 (~인천), 한국철도공사 운영
'경의중앙선'은 청량리/회기/광운대 등 일부 역을 경원선과 공유하지만 실제로는
별개의 운행 노선(수도권 전철 경의중앙선)이므로 1호선에서 제외함.

역 중복 처리:
  - 용산역처럼 동일 역번호(예: 1003)가 경원선/경부선 둘 다에 등장하는 경우가 있어
    역번호 기준으로 중복 제거함.

[9호선 / 8호선 처리]
  - 9호선: '서울 도시철도 9호선' + '수도권  도시철도 9호선'(공백 2칸) 통합
  - 8호선: '8호선'(본선) + '수도권 광역철도 8호선'(별내선 연장) 통합
- '도시철도 7호선'은 인천교통공사가 운영하는 인천지하철 7호선이라 제외함.

[정렬 방침]
  - station_id가 각 노선 내에서 실제 역 순서를 따라 순차 부여되어 있음을 확인함
    (예: 2호선 0201→0202→..., 신분당선 D004→D005→...).
  - 2~9호선/신분당선: station_id 오름차순 = 실제 노선 순서.
  - 1호선: 4개 원본 구간이 각자 독립된 station_id 체계를 쓰므로, 구간 단위로
    지리적 흐름(소요산→도심→경부선→경인선)에 맞게 배치한 뒤 구간 내부는
    station_id 순으로 정렬함. 단, 구로역 이후 경부선(~천안)과 경인선(~인천)이
    두 갈래로 갈라지는 분기 구조라 완전한 단일 직선 순서는 아니며, 편의상
    경부선 뒤에 경인선을 이어붙인 근사치임 (자세한 내용은 아래 sort_key 참고).

주의사항 (미해결 이슈, 후속 확인 필요):
- 2호선의 신정지선/성수지선 등 분기 구간은 원본 '노선명'이 본선과 동일하게
  표기되어 있을 수 있어, build_graph.py에서 역번호 순으로 인접 연결할 때
  분기 구간이 잘못 이어질 수 있음. station_graph.json 생성 후 지도로 검증 필요.
- 경인선의 소사역(station_id 4804)처럼 예외적으로 번호 체계가 다른 역이
  있어 station_id 정렬만으로는 지리적 순서가 깨질 수 있음.
"""

import csv
import json
from pathlib import Path

import openpyxl

RAW_DIR = Path(__file__).resolve().parents[1] / "raw"
OUT_DIR = Path(__file__).resolve().parents[1] / "processed"
OUT_JSON = OUT_DIR / "seoul_lines_normalized.json"
OUT_CSV = OUT_DIR / "seoul_lines_normalized.csv"

SHEET_NAME = "표준데이터 역사"

# 소요산 이후 경원선 제외 대상 (지하철 서비스 구간 밖)
GYEONGWON_EXCLUDE_AFTER_SOYOSAN = {"청산역", "전곡역", "연천역"}

# 1호선을 구성하는 원본 노선명들
LINE1_SOURCE_LINES = ["1호선", "경원선", "경부선", "경인선"]

# 그 외 포함할 노선 (원본 노선명 기준)
OTHER_TARGET_LINES = [
    "2호선", "3호선", "4호선", "5호선", "6호선", "7호선", "8호선",
    "수도권 광역철도 8호선",      # 8호선 별내선 연장
    "서울 도시철도 9호선",        # 9호선 1단계
    "수도권  도시철도 9호선",     # 9호선 2단계 (원본 노선명에 공백 2칸)
    "신분당선",
]

# 노선명 표준화 매핑 (통합 표시용)
LINE_NAME_NORMALIZE = {
    "수도권 광역철도 8호선": "8호선",
    "서울 도시철도 9호선": "9호선",
    "수도권  도시철도 9호선": "9호선",
    "경원선": "1호선",
    "경부선": "1호선",
    "경인선": "1호선",
}

TRANSFER_TRUE_VALUES = {"환승역", "도시철도 환승역"}

# 정렬 순서 (1~9호선, 신분당선 순)
LINE_ORDER = ["1호선", "2호선", "3호선", "4호선", "5호선", "6호선", "7호선", "8호선", "9호선", "신분당선"]
LINE_ORDER_MAP = {name: i for i, name in enumerate(LINE_ORDER)}

# 1호선 내부 구간 배치 순서 (지리적 흐름: 소요산 -> 도심 -> 남/서쪽 방향)
# (배치순서, station_id 내림차순 여부)
LINE1_SEGMENT_ORDER = {
    "경원선": (0, True),   # 소요산(북, id 큼) -> 용산 방향(id 작음)
    "1호선": (1, False),   # 청량리 -> 서울역
    "경부선": (2, False),  # 남영 -> 천안/광명
    "경인선": (3, False),  # 개봉 -> 인천
}

# 경부선/경인선은 나중에 신설된 역(온수·중동·소사·도화·간석·도원·부개·구일·독산·
# 신길·당정 등)이 기존 역 사이에 끼워 넣어지면서 역번호가 실제 노선 순서를 따르지
# 않는다. station_id 정렬 대신 검증된 실제 순서를 직접 지정한다.
# 서동탄역(병점역에서 갈라지는 지선 종점)과 광명역(금천구청역에서 갈라지는 셔틀
# 지선 종점)은 본선이 아니므로 이 목록에서 빼고, build_graph.py에서 SPUR로
# 별도 연결한다.
MANUAL_LINE_ORDER = {
    "경부선": [
        "남영역", "용산역", "노량진", "대방역", "신길", "영등포역", "신도림", "구로역",
        "가산디지털단지", "독산역", "금천구청역", "석수역", "관악역", "안양역", "명학역",
        "금정역", "군포역", "당정역", "의왕역", "성균관대역", "화서역", "수원역", "세류역",
        "병점역", "세마역", "오산대역", "오산역", "진위역", "송탄역", "서정리역",
        "평택지제역", "평택역", "성환역", "직산역", "두정역", "천안역",
    ],
    "경인선": [
        "구일역", "개봉역", "오류동역", "온수역", "역곡역", "소사역", "부천역", "중동역",
        "송내역", "부개역", "부평역", "백운역", "동암역", "간석역", "주안역", "도화역",
        "제물포역", "도원역", "동인천역", "인천역",
    ],
}

SPUR_STATIONS = {"서동탄역", "광명역"}


def find_raw_xlsx() -> Path:
    files = sorted(RAW_DIR.glob("*.xlsx"))
    if not files:
        raise FileNotFoundError(
            f"{RAW_DIR}에 원본 xlsx가 없습니다. data.go.kr에서 내려받아 이 폴더에 넣어주세요."
        )
    return files[-1]  # 날짜가 포함된 파일명 기준으로 가장 최신 파일 사용


def load_rows(src: Path):
    wb = openpyxl.load_workbook(src, read_only=True)
    ws = wb[SHEET_NAME]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    return header, rows[1:]


def _split_station_id(sid):
    """station_id를 (알파벳 접두사, 숫자) 로 분리. 자릿수가 3/4자리로 섞여있어
    문자열 비교로는 순서가 깨지므로(예: '807' vs '1002') 숫자로 변환해서 비교."""
    sid = str(sid)
    prefix = "".join(c for c in sid if not c.isdigit())
    digits = "".join(c for c in sid if c.isdigit())
    return prefix, int(digits) if digits else 0


def sort_key(d: dict):
    line_name = d["line_name"]
    line_idx = LINE_ORDER_MAP.get(line_name, 999)
    raw = d["line_name_raw"]

    manual_order = MANUAL_LINE_ORDER.get(raw)
    if manual_order is not None:
        seg_order, _ = LINE1_SEGMENT_ORDER.get(raw, (99, False))
        if d["station_name"] in manual_order:
            return (line_idx, seg_order, manual_order.index(d["station_name"]))
        # 서동탄/광명 같은 스퍼 역은 본선 순서 뒤쪽에 배치(순서 자체는 의미 없음,
        # build_graph.py가 본선 시퀀스에서 제외하고 별도 스퍼 엣지로 연결한다)
        return (line_idx, seg_order, len(manual_order) + 1)

    prefix, num = _split_station_id(d["station_id"])
    if line_name == "1호선":
        seg_order, reverse = LINE1_SEGMENT_ORDER.get(raw, (99, False))
        num_key = -num if reverse else num
        return (line_idx, seg_order, prefix, num_key)
    return (line_idx, 0, prefix, num)


# 단순 '역' 접미사 유무로는 안 잡히는 표기 차이(괄호 부기명 등)를 수동으로 통일.
# 청량리는 1호선(급행/완행 도심 구간) 레코드에서 '청량리(서울시립대입구)'로,
# 경원선(완행 북부 구간) 레코드에서 '청량리역'으로 서로 다르게 표기되어 있어
# 같은 물리적 환승역인데 두 노드로 쪼개진다. (담당1 수동 검증, 2026-08-15)
STATION_NAME_ALIASES = {
    "청량리(서울시립대입구)": "청량리역",
}


def _unify_station_name_variants(records: list[dict]) -> None:
    """일부 환승역이 1호선 데이터에서는 '역' 접미사가 붙고(예: '신도림역') 다른
    노선에서는 안 붙어(예: '신도림') 같은 물리적 역이 서로 다른 이름으로 쪼개지는
    문제를 막는다. '역'을 뗀 이름이 이미 다른 노선에 존재하면 그 표기로 통일해서
    station_name 기준 노드 병합(build_graph.py)이 정상 동작하게 한다."""
    for r in records:
        if r["station_name"] in STATION_NAME_ALIASES:
            r["station_name"] = STATION_NAME_ALIASES[r["station_name"]]

    names = {r["station_name"] for r in records}
    for r in records:
        name = r["station_name"]
        if name.endswith("역") and name[:-1] in names:
            r["station_name"] = name[:-1]


def normalize(src: Path) -> list[dict]:
    header, data = load_rows(src)
    col = {name: i for i, name in enumerate(header)}

    all_target_lines = LINE1_SOURCE_LINES + OTHER_TARGET_LINES
    seen_station_ids: set = set()
    result = []

    for r in data:
        line_name = r[col["노선명"]]
        if line_name not in all_target_lines:
            continue

        station_name = r[col["역사명"]]

        # 경원선의 소요산 이후 구간 제외
        if line_name == "경원선" and station_name in GYEONGWON_EXCLUDE_AFTER_SOYOSAN:
            continue

        station_id = r[col["역번호"]]

        # 동일 역번호 중복 제거 (예: 용산역이 경원선/경부선에 동시 등장)
        if station_id in seen_station_ids:
            continue
        seen_station_ids.add(station_id)

        normalized_line = LINE_NAME_NORMALIZE.get(line_name, line_name)
        is_transfer = r[col["환승역구분"]] in TRANSFER_TRUE_VALUES

        result.append({
            "station_id": station_id,
            "station_name": station_name,
            "line_code": r[col["노선번호"]],
            "line_name": normalized_line,
            "line_name_raw": line_name,          # 원본 노선명 (디버깅용)
            "name_en": r[col["영문역사명"]],
            "is_transfer": is_transfer,
            "transfer_line_name": r[col["환승노선명"]],
            "lat": r[col["역위도"]],
            "lng": r[col["역경도"]],
            "operator": r[col["운영기관명"]],
            "address": r[col["역사도로명주소"]],
        })

    _unify_station_name_variants(result)

    # 실제 노선 순서(station_id 기준) 정렬
    result.sort(key=sort_key)
    return result


def main() -> None:
    src = find_raw_xlsx()
    stations = normalize(src)
    print(f"원본: {src.name}")
    print(f"정규화된 역 레코드 수: {len(stations)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(stations, f, ensure_ascii=False, indent=2)

    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=stations[0].keys())
        writer.writeheader()
        writer.writerows(stations)

    print(f"완료: {OUT_JSON.name} / {OUT_CSV.name} 저장됨")


if __name__ == "__main__":
    main()
