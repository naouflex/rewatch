import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import HelpSidebar from "./HelpSidebar.jsx";
import useEmbedMode from "../hooks/useEmbedMode.js";

export default function HelpLayout({ children }) {
  const embed = useEmbedMode();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  // Auto-close the slide-in menu whenever the route changes (covers the
  // case where the user picks a topic — also reliable if something else
  // navigates programmatically).
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  // Lock background scroll while the embed overlay is open and let users
  // dismiss it with the Escape key.
  useEffect(() => {
    if (!menuOpen) return undefined;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  if (embed) {
    return (
      <div className="container help-layout help-layout--embed">
        <main className="help-content help-content--embed">
          <div className="help-embed-bar">
            <button
              type="button"
              className="help-menu-toggle"
              onClick={() => setMenuOpen(true)}
              aria-expanded={menuOpen}
              aria-controls="help-sidebar-embed"
              aria-label="Open help topics menu"
            >
              <span className="help-menu-toggle__icon" aria-hidden="true">
                <span />
                <span />
                <span />
              </span>
              <span>Menu</span>
            </button>
          </div>
          {children}
        </main>

        {menuOpen && (
          <div
            className="help-menu-overlay"
            role="dialog"
            aria-modal="true"
            aria-label="Help topics"
          >
            <button
              type="button"
              className="help-menu-overlay__backdrop"
              aria-label="Close help topics menu"
              onClick={() => setMenuOpen(false)}
            />
            <div className="help-menu-overlay__panel">
              <div className="help-menu-overlay__header">
                <strong>Help topics</strong>
                <button
                  type="button"
                  className="help-menu-overlay__close"
                  onClick={() => setMenuOpen(false)}
                  aria-label="Close help topics menu"
                >
                  ×
                </button>
              </div>
              <div className="help-menu-overlay__body">
                <HelpSidebar
                  idPrefix="help-sidebar-embed"
                  onNavigate={() => setMenuOpen(false)}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="container help-layout">
      <HelpSidebar />
      <main className="help-content">{children}</main>
    </div>
  );
}
