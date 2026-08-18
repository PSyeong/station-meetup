import { Routes, Route } from "react-router-dom";
import NavBar from "./components/NavBar.jsx";
import Home from "./pages/Home.jsx";
import SubwayMapPage from "./pages/SubwayMapPage.jsx";

export default function App() {
  return (
    <div className="app-viewport">
      <div className="app-frame">
        <div className="app-shell">
          <main className="app-main">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/subway-map" element={<SubwayMapPage />} />
            </Routes>
          </main>
          <NavBar />
        </div>
      </div>
    </div>
  );
}
