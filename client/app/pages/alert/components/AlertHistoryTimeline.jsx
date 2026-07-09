import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import moment from "moment";
import cx from "classnames";
import Spin from "antd/lib/spin";
import Tooltip from "@/components/Tooltip";

import AlertEvents from "@/services/alert-events";
import { statusTag } from "@/pages/alert-events/alertEventUtils";

import "./AlertHistoryTimeline.less";

const HOURS = 24;

function bucketByHour(events) {
  const now = moment();
  const start = now.clone().subtract(HOURS, "hours").startOf("hour");
  const buckets = [];

  for (let i = 0; i < HOURS; i += 1) {
    const hourStart = start.clone().add(i, "hours");
    const hourEnd = hourStart.clone().add(1, "hour");
    const inBucket = events.filter(event => {
      const created = moment(event.created_at);
      return created.isSameOrAfter(hourStart) && created.isBefore(hourEnd);
    });
    buckets.push({
      label: hourStart.format("HH:mm"),
      events: inBucket,
      hasError: inBucket.some(event => event.status === "error"),
      hasOk: inBucket.some(event => event.status !== "error"),
    });
  }

  return buckets;
}

export default function AlertHistoryTimeline({ alertId, refreshToken }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    AlertEvents.forAlert({ alertId, page: 1, pageSize: 100 })
      .then(({ results }) => {
        if (!cancelled) {
          const cutoff = moment().subtract(HOURS, "hours");
          setEvents((results || []).filter(event => moment(event.created_at).isAfter(cutoff)));
        }
      })
      .catch(() => {
        if (!cancelled) {
          setEvents([]);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [alertId, refreshToken]);

  const buckets = useMemo(() => bucketByHour(events), [events]);
  const hasActivity = events.length > 0;

  if (loading) {
    return (
      <div className="alert-history-timeline alert-history-timeline--loading">
        <Spin size="small" />
      </div>
    );
  }

  if (!hasActivity) {
    return (
      <div className="alert-history-timeline alert-history-timeline--empty">
        No notifications in the last {HOURS} hours.
      </div>
    );
  }

  return (
    <div className="alert-history-timeline" data-test="AlertHistoryTimeline">
      <div className="alert-history-timeline__label">Last {HOURS} hours</div>
      <div className="alert-history-timeline__track">
        {buckets.map((bucket, index) => (
          <Tooltip
            key={index}
            title={
              bucket.events.length
                ? `${bucket.events.length} notification${bucket.events.length > 1 ? "s" : ""} at ${bucket.label}`
                : `No notifications at ${bucket.label}`
            }>
            <div
              className={cx("alert-history-timeline__slot", {
                "alert-history-timeline__slot--ok": bucket.hasOk,
                "alert-history-timeline__slot--error": bucket.hasError,
                "alert-history-timeline__slot--empty": !bucket.events.length,
              })}
            />
          </Tooltip>
        ))}
      </div>
      <div className="alert-history-timeline__legend">
        <span className="alert-history-timeline__legend-item alert-history-timeline__legend-item--ok">Delivered</span>
        <span className="alert-history-timeline__legend-item alert-history-timeline__legend-item--error">Failed</span>
      </div>
      <div className="alert-history-timeline__recent">
        {events.slice(0, 3).map(event => (
          <span key={event.id} className="alert-history-timeline__event">
            {moment(event.created_at).format("HH:mm")} {statusTag(event.status)}
          </span>
        ))}
      </div>
    </div>
  );
}

AlertHistoryTimeline.propTypes = {
  alertId: PropTypes.any.isRequired,
  refreshToken: PropTypes.number,
};

AlertHistoryTimeline.defaultProps = {
  refreshToken: 0,
};
