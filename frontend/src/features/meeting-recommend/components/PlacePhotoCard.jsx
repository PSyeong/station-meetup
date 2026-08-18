export default function PlacePhotoCard({ place }) {
  const [from, to] = place.image?.gradient || ["#d2d2d7", "#a1a1a6"];

  return (
    <div className="place-photo-card">
      <div className="place-photo-card__image" style={{ background: `linear-gradient(135deg, ${from}, ${to})` }}>
        <span className="place-photo-card__emoji">{place.image?.emoji}</span>
      </div>
      <div className="place-photo-card__body">
        <div className="place-photo-card__name">{place.name}</div>
        <div className="place-photo-card__address">{place.road_address || place.address}</div>
        <div className="place-photo-card__desc">{place.description}</div>
      </div>
    </div>
  );
}
