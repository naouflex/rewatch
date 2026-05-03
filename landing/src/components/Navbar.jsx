import { NavLink, Link } from "react-router-dom";
import ThemeToggle from "./ThemeToggle.jsx";

const NAV_LINKS = [
  { to: "/", label: "Home", end: true },
  { to: "/work", label: "Work" },
  { to: "/blog", label: "Blog" },
  { to: "/help", label: "Help" },
];

export default function Navbar() {
  return (
    <header className="navbar">
      <div className="container navbar__inner">
        <Link to="/" className="navbar__brand">
          <img
            src="/logo.png"
            alt=""
            className="navbar__logo-img"
            aria-hidden="true"
          />
          <span>Analytics · Landing</span>
        </Link>
        <nav className="navbar__links" aria-label="Primary">
          {NAV_LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                "navbar__link" + (isActive ? " is-active" : "")
              }
            >
              {link.label}
            </NavLink>
          ))}
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
