const SUPPORTED_CATEGORIES = ["맛집", "카페", "놀거리"]
const DEFAULT_LIMIT = 5

const NAME_POOLS = {
  맛집: [
    "명가 백반",
    "이든 파스타",
    "역전회관",
    "청기와 돈까스",
    "미가 초밥",
    "온기 국밥",
    "산들 삼겹살",
  ],
  카페: [
    "카페 온화",
    "블랙브릭 커피",
    "테라로사",
    "모모스 커피",
    "리버뷰 카페",
    "오후의 홍차",
  ],
  놀거리: [
    "방탈출 미스터리룸",
    "보드게임카페 다이스",
    "볼링펀 볼링장",
    "메가박스",
    "예술의숲 전시관",
  ],
}

const DESCRIPTION_POOLS = {
  맛집: [
    "가볍게 끼니를 해결하기 좋은 곳",
    "든든하게 먹고 싶을 때 추천",
    "웨이팅이 있어도 아깝지 않은 맛",
  ],
  카페: [
    "대화하며 쉬어가기 좋은 분위기",
    "커피 맛으로 소문난 곳",
    "조용히 이야기 나누기 좋은 자리",
  ],
  놀거리: [
    "둘이서도, 여럿이서도 즐거운 곳",
    "심심할 틈 없이 시간 가는 곳",
    "만나서 뭐할지 고민될 때 딱",
  ],
}

const CATEGORY_EMOJI = { 맛집: "🍜", 카페: "☕", 놀거리: "🎳" }
const CATEGORY_GRADIENTS = {
  맛집: ["#ffb199", "#ff6a6a"],
  카페: ["#c9a27e", "#8a5a3b"],
  놀거리: ["#8ec5ff", "#5c7cfa"],
}

function hashSeed(str) {
  let h = 2166136261
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return h >>> 0
}

function mulberry32(seed) {
  let a = seed
  return function () {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function generatePlacesForCategory(stationName, category, limit, rand) {
  const pool = NAME_POOLS[category]
  const descriptions = DESCRIPTION_POOLS[category]
  const count = Math.min(limit, pool.length)
  const shuffled = [...pool].sort(() => rand() - 0.5).slice(0, count)
  return shuffled
    .map((name) => ({
      name: `${stationName} ${name}`,
      distance_m: Math.round(80 + rand() * 900),
      address: `서울 ${stationName} 인근`,
      road_address: `서울 ${stationName} 인근`,
      latitude: null,
      longitude: null,
      url: null,
      description: descriptions[Math.floor(rand() * descriptions.length)],
      image: {
        emoji: CATEGORY_EMOJI[category],
        gradient: CATEGORY_GRADIENTS[category],
      },
    }))
    .sort((a, b) => a.distance_m - b.distance_m)
}

// 백엔드 recommend_places_for_selection()과 동일한 반환 shape의 mock 함수.
// 실제 Kakao Local API 대신 결정적(deterministic) 목업 데이터를 사용한다 — API 연동 시 이 파일만 교체하면 된다.
export function generateMockPlaces({
  meetingStations,
  selectedIndex,
  categories = SUPPORTED_CATEGORIES,
  limit = DEFAULT_LIMIT,
}) {
  if (!meetingStations || meetingStations.length === 0) {
    throw new Error("선택할 추천역 결과가 없습니다.")
  }
  if (
    !Number.isInteger(selectedIndex) ||
    selectedIndex < 0 ||
    selectedIndex >= meetingStations.length
  ) {
    throw new Error(
      `추천역 선택 인덱스가 범위를 벗어났습니다: ${selectedIndex}`
    )
  }

  const selected = meetingStations[selectedIndex]
  const stationName = selected.station

  const places = Object.fromEntries(
    categories.map((category) => {
      const rand = mulberry32(hashSeed(`${stationName}::${category}`))
      return [
        category,
        generatePlacesForCategory(stationName, category, limit, rand),
      ]
    })
  )

  return {
    selected_index: selectedIndex,
    selected_station: stationName,
    selected_recommendation: selected,
    places,
  }
}
