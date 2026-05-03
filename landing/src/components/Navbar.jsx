import { NavLink, Link } from "react-router-dom";

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
          <span className="navbar__logo" aria-hidden="true">R</span>
          <span>Redash · Landing</span>
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
        </nav>
      </div>
    </header>
  );
}
