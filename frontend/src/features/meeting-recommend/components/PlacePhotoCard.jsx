import { CATEGORY_EMOJI, CATEGORY_GRADIENTS, lastCategorySegment } from "../placeVisuals.js";

export default function PlacePhotoCard({ place, category }) {
  const [from, to] = CATEGORY_GRADIENTS[category] || ["#d2d2d7", "#a1a1a6"];
  const emoji = CATEGORY_EMOJI[category] || "📍";

  return (
    <a
      className="place-photo-card"
      href={place.place_url || undefined}
      target={place.place_url ? "_blank" : undefined}
      rel={place.place_url ? "noreferrer" : undefined}
    >
      <div className="place-photo-card__image" style={{ background: `linear-gradient(135deg, ${from}, ${to})` }}>
        <span className="place-photo-card__emoji">{emoji}</span>
      </div>
      <div className="place-photo-card__body">
        <div className="place-photo-card__name">{place.name}</div>
        <div className="place-photo-card__address">{place.road_address || place.address}</div>
        <div className="place-photo-card__desc">{lastCategorySegment(place.category)}</div>
      </div>
    </a>
  );
}
