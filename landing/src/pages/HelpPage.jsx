import { useCallback, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import HelpLayout from "../components/HelpLayout.jsx";
import { HELP_TOPICS_BY_PATH } from "../data/helpTopics.js";
import useIframeUrlBridge from "../hooks/useIframeUrlBridge.js";
import embedHref from "../utils/embedHref.js";

export default function HelpPage() {
  useIframeUrlBridge();
  const location = useLocation();
  const navigate = useNavigate();

  // Body content is injected via dangerouslySetInnerHTML so its <a>
  // tags bypass React Router. Intercept clicks on internal links so
  // they route through the SPA and keep the ?embed=1/?theme=… search
  // params intact when running inside the help drawer.
  const handleBodyClick = useCallback(
    (event) => {
      const anchor = event.target.closest && event.target.closest("a");
      if (!anchor) return;
      if (event.defaultPrevented) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      if (event.button !== undefined && event.button !== 0) return;
      if (anchor.target && anchor.target !== "" && anchor.target !== "_self") return;
      const href = anchor.getAttribute("href");
      if (!href) return;
      if (!href.startsWith("/")) return;
      event.preventDefault();
      navigate(embedHref(href));
    },
    [navigate]
  );

  // Drop the leading "/help" prefix so we can look the topic up in the
  // shared registry. Strip the trailing slash some links from the host
  // app may include.
  const topicPath = location.pathname.replace(/^\/help/, "").replace(/\/$/, "");
  const topic = HELP_TOPICS_BY_PATH[topicPath];

  // If the URL contains a hash (e.g. /help/...#Value-Source-Options),
  // scroll to it once the content has rendered.
  useEffect(() => {
    if (!location.hash) return;
    const el = document.getElementById(location.hash.replace("#", ""));
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [location.hash, topic]);

  if (!topic) {
    return (
      <HelpLayout>
        <p className="help-breadcrumbs">
          <Link to={embedHref("/help")}>Help</Link>
          {topicPath.split("/").map((segment, idx, arr) => {
            if (!segment) return null;
            const partial = arr.slice(0, idx + 1).join("/");
            return (
              <span key={partial}>
                {" "}/ <Link to={embedHref(`/help/${partial}`)}>{segment}</Link>
              </span>
            );
          })}
        </p>
        <h1>Page not found</h1>
        <p className="lead">
          We don&rsquo;t have a guide for this topic yet.
        </p>
        <div className="help-empty">
          Pick another topic from the menu, or head back to the{" "}
          <Link to={embedHref("/help")}>help home</Link>.
        </div>
      </HelpLayout>
    );
  }

  return (
    <HelpLayout>
      <p className="help-breadcrumbs">
        <Link to={embedHref("/help")}>Help</Link> &nbsp;/&nbsp; {topic.title}
      </p>
      <h1>{topic.title}</h1>
      {topic.summary && <p className="lead">{topic.summary}</p>}
      {topic.body ? (
        <div
          onClick={handleBodyClick}
          dangerouslySetInnerHTML={{ __html: topic.body }}
        />
      ) : (
        <div className="help-empty">
          Detailed write-up coming soon. In the meantime, pick another topic
          from the menu.
        </div>
      )}
    </HelpLayout>
  );
}
