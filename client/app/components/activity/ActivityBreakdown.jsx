import React from "react";
import PropTypes from "prop-types";

import "./ActivityBreakdown.less";

function BreakdownList({ title, items }) {
  if (!items?.length) {
    return null;
  }

  const maxCount = Math.max(...items.map(item => item.count), 1);

  return (
    <div className="activity-breakdown__list">
      <h4 className="activity-breakdown__list-title">{title}</h4>
      <ul className="activity-breakdown__items">
        {items.slice(0, 6).map(item => (
          <li key={item.key} className="activity-breakdown__item">
            <span className="activity-breakdown__label">{item.label}</span>
            <span className="activity-breakdown__bar-wrap">
              <span
                className="activity-breakdown__bar"
                style={{ width: `${Math.max(8, (item.count / maxCount) * 100)}%` }}
              />
            </span>
            <span className="activity-breakdown__count">{item.count}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

BreakdownList.propTypes = {
  title: PropTypes.string.isRequired,
  items: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
      count: PropTypes.number.isRequired,
    })
  ),
};

BreakdownList.defaultProps = {
  items: [],
};

export default function ActivityBreakdown({ byAction, byObjectType }) {
  if (!byAction?.length && !byObjectType?.length) {
    return (
      <p className="activity-breakdown__empty">
        Run queries, edit dashboards, or create content to build your activity history.
      </p>
    );
  }

  return (
    <div className="activity-breakdown">
      <BreakdownList title="By action" items={byAction} />
      <BreakdownList title="By resource" items={byObjectType} />
    </div>
  );
}

ActivityBreakdown.propTypes = {
  byAction: PropTypes.array,
  byObjectType: PropTypes.array,
};

ActivityBreakdown.defaultProps = {
  byAction: [],
  byObjectType: [],
};
