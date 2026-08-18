import { NavLink } from "react-router-dom";
import { Home, TrainFront } from "lucide-react";

const TABS = [
  { to: "/", label: "홈", Icon: Home, end: true },
  { to: "/subway-map", label: "노선도", Icon: TrainFront },
];

export default function NavBar() {
  return (
    <nav className="tab-bar">
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.end}
          className={({ isActive }) => "tab-bar__item" + (isActive ? " tab-bar__item--active" : "")}
        >
          <tab.Icon className="tab-bar__icon" size={20} strokeWidth={2} aria-hidden="true" />
          <span className="tab-bar__label">{tab.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
