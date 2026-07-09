import React from "react";
import PropTypes from "prop-types";
import cx from "classnames";
import CheckOutlined from "@ant-design/icons/CheckOutlined";
import LoadingOutlined from "@ant-design/icons/LoadingOutlined";
import GlobalOutlined from "@ant-design/icons/GlobalOutlined";

import "./AssistantThinking.less";

function activityIcon(tool, status) {
  if (status === "done") {
    return <CheckOutlined aria-hidden="true" />;
  }
  if (tool === "web_search" || tool === "fetch_url" || tool === "discover_public_sources") {
    return <GlobalOutlined aria-hidden="true" spin={status === "running"} />;
  }
  return <LoadingOutlined aria-hidden="true" spin={status === "running"} />;
}

export default function AssistantThinking({ status, activities }) {
  return (
    <div className="assistant-thinking" aria-live="polite" aria-busy="true">
      <div className="assistant-thinking-header">
        <div className="assistant-thinking-dots" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <div className="assistant-thinking-status">{status || "Thinking…"}</div>
      </div>

      {activities.length > 0 && (
        <ul className="assistant-thinking-steps">
          {activities.map(item => (
            <li
              key={item.id}
              className={cx("assistant-thinking-step", item.status, {
                "is-web":
                  item.tool === "web_search" ||
                  item.tool === "fetch_url" ||
                  item.tool === "discover_public_sources",
              })}
            >
              <span className="assistant-thinking-step-icon">{activityIcon(item.tool, item.status)}</span>
              <span className="assistant-thinking-step-label">{item.label}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

AssistantThinking.propTypes = {
  status: PropTypes.string,
  activities: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      tool: PropTypes.string,
      label: PropTypes.string.isRequired,
      status: PropTypes.oneOf(["running", "done"]).isRequired,
    })
  ),
};

AssistantThinking.defaultProps = {
  status: "Thinking…",
  activities: [],
};
