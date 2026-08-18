import { useEffect, useState } from "react";
import "./MeetingRecommend.css";
import Spinner from "../../components/Spinner.jsx";
import InputScene from "./scenes/InputScene.jsx";
import MapResultScene from "./scenes/MapResultScene.jsx";
import PlaceListScene from "./scenes/PlaceListScene.jsx";
import { fetchRecommendations, fetchPlaces } from "./api.js";

export default function MeetingRecommend() {
  const [graph, setGraph] = useState(null);
  const [error, setError] = useState(null);
  const [scene, setScene] = useState("input");
  const [recommendations, setRecommendations] = useState(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [places, setPlaces] = useState(null);
  const [placesLoading, setPlacesLoading] = useState(false);
  const [placesError, setPlacesError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  useEffect(() => {
    fetch("/data/station_graph.json")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(setGraph)
      .catch((err) => setError(err.message));
  }, []);

  async function handleFindMeetingPoint(origins, mode) {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const results = await fetchRecommendations({ origins, mode, topK: 3 });
      setRecommendations(results);
      setSelectedIndex(0);
      setPlaces(null);
      setScene("map");
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleShowPlaces() {
    setPlacesLoading(true);
    setPlacesError(null);
    setPlaces(null);
    setScene("places");
    try {
      const stationId = recommendations[selectedIndex].station;
      const result = await fetchPlaces({ stationId });
      setPlaces(result);
    } catch (err) {
      setPlacesError(err.message);
    } finally {
      setPlacesLoading(false);
    }
  }

  if (error) {
    return (
      <div className="meeting-recommend__status">
        <p>
          <strong>역 데이터를 불러오지 못했습니다.</strong>
        </p>
        <p>data/station_graph.json이 있는지, dev 서버(npm run dev)가 실행 중인지 확인해주세요.</p>
        <p className="meeting-recommend__status-detail">{error}</p>
      </div>
    );
  }

  if (!graph) {
    return (
      <div className="meeting-recommend__status meeting-recommend__status--loading">
        <Spinner />
        불러오는 중...
      </div>
    );
  }

  if (scene === "map" && recommendations) {
    return (
      <MapResultScene
        graph={graph}
        recommendations={recommendations}
        selectedIndex={selectedIndex}
        onSelectStation={setSelectedIndex}
        onBack={() => setScene("input")}
        onShowPlaces={handleShowPlaces}
      />
    );
  }

  if (scene === "places" && recommendations) {
    return (
      <PlaceListScene
        stationName={recommendations[selectedIndex].station}
        places={places}
        loading={placesLoading}
        error={placesError}
        onBack={() => setScene("map")}
      />
    );
  }

  return (
    <InputScene
      graph={graph}
      onSubmit={handleFindMeetingPoint}
      submitting={submitting}
      submitError={submitError}
    />
  );
}
