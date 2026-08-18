export const CATEGORY_EMOJI = { 맛집: "🍜", 카페: "☕", 놀거리: "🎳" };
export const CATEGORY_GRADIENTS = {
  맛집: ["#ffb199", "#ff6a6a"],
  카페: ["#c9a27e", "#8a5a3b"],
  놀거리: ["#8ec5ff", "#5c7cfa"],
};

// Kakao 카테고리 breadcrumb("음식점 > 카페 > 커피전문점 > 빽다방")에서 가장 구체적인 마지막 조각만 뽑는다.
export function lastCategorySegment(category) {
  if (!category) return "";
  const segments = category.split(">").map((s) => s.trim());
  return segments[segments.length - 1] || category;
}
