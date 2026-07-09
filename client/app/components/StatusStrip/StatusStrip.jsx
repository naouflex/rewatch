import React from "react";
import PropTypes from "prop-types";
import cx from "classnames";

import Tag from "antd/lib/tag";

import "./StatusStrip.less";

export default function StatusStrip({ items, className }) {
  if (!items || !items.length) {
    return null;
  }

  const primary = items[0];

  return (
    <div className={cx("status-strip", className)} data-test="StatusStrip">
      {primary.color && (
        <span
          className={cx("status-strip__dot", `status-strip__dot--${primary.color}`)}
          aria-hidden="true"
        />
      )}
      <span className="status-strip__state">{primary.label}</span>
      {items.slice(1).map((item, index) => (
        <span key={item.key || index} className="status-strip__meta">
          {item.label}
        </span>
      ))}
      {items
        .filter(item => item.tag)
        .map((item, index) => (
          <Tag key={`tag-${index}`} className="status-strip__tag" color={item.tagColor || "default"}>
            {item.tag}
          </Tag>
        ))}
    </div>
  );
}

StatusStrip.propTypes = {
  items: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string,
      label: PropTypes.node,
      color: PropTypes.oneOf(["success", "warning", "error", "info"]),
      tag: PropTypes.string,
      tagColor: PropTypes.string,
    })
  ),
  className: PropTypes.string,
};

StatusStrip.defaultProps = {
  items: [],
  className: null,
};
