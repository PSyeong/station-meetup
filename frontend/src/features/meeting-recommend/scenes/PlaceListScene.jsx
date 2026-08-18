import { useState } from "react";
import { ChevronLeft } from "lucide-react";
import PlacePhotoCard from "../components/PlacePhotoCard.jsx";
import Spinner from "../../../components/Spinner.jsx";

const CATEGORIES = ["맛집", "카페", "놀거리"];

export default function PlaceListScene({ stationName, places, loading, onBack }) {
  const [category, setCategory] = useState(CATEGORIES[0]);
  const items = places?.[category] ?? [];

  return (
    <div className="scene scene--places">
      <header className="scene__header">
        <button type="button" className="scene__back" onClick={onBack} aria-label="뒤로가기">
          <ChevronLeft size={22} strokeWidth={2} />
        </button>
        <h2 className="scene__title">여기에서 뭐하지?</h2>
        <span className="scene__header-spacer" aria-hidden="true" />
      </header>

      <div className="place-list-scene__body">
        <h1 className="place-list-scene__headline">
          {stationName} 근처에서
          <br />
          여기 가보는건 어때요?
        </h1>
        <p className="place-list-scene__subcopy">고민될 땐 아래 추천을 참고해보세요</p>

        <div className="place-panel__tabs">
          {CATEGORIES.map((c) => (
            <button
              key={c}
              type="button"
              className={"place-panel__tab" + (category === c ? " place-panel__tab--active" : "")}
              onClick={() => setCategory(c)}
            >
              {c}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="place-panel__status place-panel__status--loading">
            <Spinner />
            불러오는 중...
          </div>
        ) : (
          <div className="place-list-scene__list">
            {items.map((p) => (
              <PlacePhotoCard key={p.name + p.distance_m} place={p} />
            ))}
            {items.length === 0 && <div className="place-panel__status">주변 장소가 없습니다.</div>}
          </div>
        )}
      </div>
    </div>
  );
}
