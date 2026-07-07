import React, { useMemo } from "react";
import PropTypes from "prop-types";

import Tooltip from "@/components/Tooltip";

import "./ActivityHeatmap.less";

function parseDateKey(dateKey) {
  const [year, month, day] = dateKey.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

function formatDateLabel(dateKey) {
  return parseDateKey(dateKey).toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

function levelForCount(count, maxCount) {
  if (!count) {
    return 0;
  }
  if (maxCount <= 1) {
    return 4;
  }
  const ratio = count / maxCount;
  if (ratio <= 0.25) {
    return 1;
  }
  if (ratio <= 0.5) {
    return 2;
  }
  if (ratio <= 0.75) {
    return 3;
  }
  return 4;
}

function buildWeekColumns(daily) {
  if (!daily?.length) {
    return [];
  }

  const firstDay = parseDateKey(daily[0].date).getUTCDay();
  const weeks = [];
  let currentWeek = Array.from({ length: firstDay }, () => null);

  daily.forEach(day => {
    currentWeek.push(day);
    if (currentWeek.length === 7) {
      weeks.push(currentWeek);
      currentWeek = [];
    }
  });

  if (currentWeek.length) {
    while (currentWeek.length < 7) {
      currentWeek.push(null);
    }
    weeks.push(currentWeek);
  }

  return weeks;
}

export default function ActivityHeatmap({ daily }) {
  const weeks = useMemo(() => buildWeekColumns(daily), [daily]);
  const maxCount = useMemo(() => Math.max(...(daily || []).map(item => item.count), 1), [daily]);

  if (!weeks.length) {
    return null;
  }

  return (
    <div className="activity-heatmap" aria-label="Activity calendar">
      <div className="activity-heatmap__grid">
        {weeks.map((week, weekIndex) => (
          <div key={weekIndex} className="activity-heatmap__week">
            {week.map((day, dayIndex) => {
              if (!day) {
                return <span key={`${weekIndex}-${dayIndex}`} className="activity-heatmap__cell activity-heatmap__cell--empty" />;
              }

              const level = levelForCount(day.count, maxCount);
              const label = `${formatDateLabel(day.date)} — ${day.count} contribution${day.count === 1 ? "" : "s"}`;

              return (
                <Tooltip key={day.date} title={label}>
                  <span
                    className={`activity-heatmap__cell activity-heatmap__cell--level-${level}`}
                    aria-label={label}
                  />
                </Tooltip>
              );
            })}
          </div>
        ))}
      </div>
      <div className="activity-heatmap__legend" aria-hidden="true">
        <span>Less</span>
        {[0, 1, 2, 3, 4].map(level => (
          <span key={level} className={`activity-heatmap__cell activity-heatmap__cell--level-${level}`} />
        ))}
        <span>More</span>
      </div>
    </div>
  );
}

ActivityHeatmap.propTypes = {
  daily: PropTypes.arrayOf(
    PropTypes.shape({
      date: PropTypes.string.isRequired,
      count: PropTypes.number.isRequired,
    })
  ),
};

ActivityHeatmap.defaultProps = {
  daily: [],
};
