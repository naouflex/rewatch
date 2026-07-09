import React from "react";
import PropTypes from "prop-types";

import TimeAgo from "@/components/TimeAgo";
import StatusStrip from "@/components/StatusStrip/StatusStrip";

const STATE_COLORS = {
  unknown: "warning",
  ok: "success",
  triggered: "error",
};

export default function AlertStatusStrip({ state, lastTriggered, queryDataAt, muted }) {
  const items = [
    {
      label: (state || "unknown").toUpperCase() === "OK" ? "OK" : state === "triggered" ? "Triggered" : "Unknown",
      color: STATE_COLORS[state] || "warning",
    },
  ];

  if (state === "unknown") {
    items.push({ label: "Condition has not been evaluated yet" });
  }
  if (lastTriggered) {
    items.push({ label: <>Last notified <TimeAgo date={lastTriggered} /></> });
  }
  if (queryDataAt) {
    items.push({ label: <>Query data from <TimeAgo date={queryDataAt} /></> });
  }
  if (muted) {
    items[0].tag = "Muted";
    items[0].tagColor = "warning";
  }

  return <StatusStrip items={items} className="alert-status-strip" />;
}

AlertStatusStrip.propTypes = {
  state: PropTypes.string.isRequired,
  lastTriggered: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  queryDataAt: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  muted: PropTypes.bool,
};

AlertStatusStrip.defaultProps = {
  lastTriggered: null,
  queryDataAt: null,
  muted: false,
};
