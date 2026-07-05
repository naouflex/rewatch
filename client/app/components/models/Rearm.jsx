import React from "react";
import PropTypes from "prop-types";
import Select from "antd/lib/select";

import "./Rearm.less";

function DisabledInput({ children, minWidth }) {
  return (
    <div className="rearm-disabled-input" style={{ minWidth }}>
      {children}
    </div>
  );
}

DisabledInput.propTypes = {
  children: PropTypes.node.isRequired,
  minWidth: PropTypes.number.isRequired,
};

export default function Rearm({ value, onChange, editMode, rearmType }) {
  const handleRearmChange = (newValue) => {
    onChange(newValue);
  };

  const getRearmText = (val) => {
    switch (val) {
      case "always":
        return "Always send notifications";
      case "never":
        return "Never send notifications";
      case "metrics":
        return rearmType === 'train' ? "Send notifications based on model metrics" : "Unknown";
      default:
        return "Unknown";
    }
  };

  return (
    <div data-test="Rearm" className="model-rearm">
      <div className="input-title">
        <span className="input-label">Rearm</span>
        {editMode ? (
          <Select
            value={value}
            onChange={handleRearmChange}
            popupMatchSelectWidth={false}
            style={{ minWidth: 150 }}>
            <Select.Option value="always">Always send notifications</Select.Option>
            <Select.Option value="never">Never send notifications</Select.Option>
            {rearmType === 'train' && (
              <Select.Option value="metrics">Send notifications based on model metrics</Select.Option>
            )}
          </Select>
        ) : (
          <DisabledInput minWidth={150}>
            {getRearmText(value)}
          </DisabledInput>
        )}
      </div>
    </div>
  );
}

Rearm.propTypes = {
  value: PropTypes.oneOf(['always', 'never', 'metrics', 'unknown']).isRequired,
  onChange: PropTypes.func,
  editMode: PropTypes.bool,
  rearmType: PropTypes.oneOf(['train', 'predict']).isRequired,
};

Rearm.defaultProps = {
  onChange: () => {},
  editMode: false,
};
