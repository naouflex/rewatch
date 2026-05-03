import { NavLink } from "react-router-dom";
import { HELP_GROUPS } from "../data/helpTopics.js";
import embedHref from "../utils/embedHref.js";

// `onNavigate` is called whenever the user picks any link in the sidebar.
// HelpLayout uses it in embed mode to auto-close the slide-in menu.
export default function HelpSidebar({ onNavigate, idPrefix = "help-sidebar" }) {
  const handleClick = () => {
    if (typeof onNavigate === "function") onNavigate();
  };

  return (
    <aside className="help-sidebar" aria-label="Help navigation" id={idPrefix}>
      <div className="help-sidebar__group">
        <h4 className="help-sidebar__title">Overview</h4>
        <ul className="help-sidebar__list">
          <li>
            <NavLink
              to={embedHref("/help")}
              end
              onClick={handleClick}
              className={({ isActive }) =>
                "help-sidebar__link" + (isActive ? " is-active" : "")
              }
            >
              Help home
            </NavLink>
          </li>
        </ul>
      </div>
      {HELP_GROUPS.map((group) => (
        <div key={group.id} className="help-sidebar__group">
          <h4 className="help-sidebar__title">{group.title}</h4>
          <ul className="help-sidebar__list">
            {group.topics.map((topic) => (
              <li key={topic.id}>
                <NavLink
                  to={embedHref(`/help${topic.path}`)}
                  onClick={handleClick}
                  className={({ isActive }) =>
                    "help-sidebar__link" + (isActive ? " is-active" : "")
                  }
                >
                  {topic.title}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </aside>
  );
}
