import { NavLink } from "react-router-dom";
import { HELP_GROUPS } from "../data/helpTopics.js";

export default function HelpSidebar() {
  return (
    <aside className="help-sidebar" aria-label="Help navigation">
      <div className="help-sidebar__group">
        <h4 className="help-sidebar__title">Overview</h4>
        <ul className="help-sidebar__list">
          <li>
            <NavLink
              to="/help"
              end
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
                  to={`/help${topic.path}`}
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
