import { NavLink } from "react-router-dom";

const TABS = [
  { to: "/", label: "홈", end: true },
  { to: "/subway-map", label: "지하철 노선도" },
];

export default function NavBar() {
  return (
    <header className="nav-bar">
      <div className="nav-bar__brand">
        <span className="nav-bar__mark" aria-hidden="true" />
        <span>만남역 추천</span>
      </div>
      <nav className="nav-bar__tabs">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) => "nav-bar__tab" + (isActive ? " nav-bar__tab--active" : "")}
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}
