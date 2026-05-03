import { Link } from "react-router-dom";
import HelpLayout from "../components/HelpLayout.jsx";
import { HELP_GROUPS } from "../data/helpTopics.js";
import useIframeUrlBridge from "../hooks/useIframeUrlBridge.js";
import embedHref from "../utils/embedHref.js";

export default function HelpHome() {
  useIframeUrlBridge();

  return (
    <HelpLayout>
      <h1>Help center</h1>
      <p className="lead">
        Documentation for the analytics tool. Pick a topic from the list
        below.
      </p>

      <div className="divider" />

      {HELP_GROUPS.map((group) => (
        <section key={group.id} style={{ marginBottom: "1.75rem" }}>
          <h2 style={{ fontSize: "1.15rem" }}>{group.title}</h2>
          <ul style={{ paddingLeft: "1.25rem", margin: 0 }}>
            {group.topics.map((topic) => (
              <li key={topic.id} style={{ marginBottom: "0.35rem" }}>
                <Link to={embedHref(`/help${topic.path}`)}>{topic.title}</Link>
                <span className="muted"> — {topic.summary}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </HelpLayout>
  );
}
