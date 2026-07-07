import React from "react";
import Tag from "antd/lib/tag";

const STATUS_COLORS = {
  ok: "green",
  error: "red",
};

export function statusTag(status) {
  if (!status) {
    return null;
  }
  return <Tag color={STATUS_COLORS[status] || "blue"}>{status.toUpperCase()}</Tag>;
}

export function destinationLabel(event) {
  if (event.destination) {
    return `${event.destination.name} (${event.destination.type})`;
  }
  if (event.alert_type) {
    return event.alert_type;
  }
  return "—";
}
