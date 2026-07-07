import React from "react";
import PropTypes from "prop-types";
import cx from "classnames";
import Button from "antd/lib/button";
import Badge from "antd/lib/badge";
import Tooltip from "@/components/Tooltip";
import KeyboardShortcuts from "@/services/KeyboardShortcuts";

function ParameterApplyButton({ paramCount, onClick, inline }) {
  if (!paramCount) {
    return null;
  }

  const icon = (
    <i className="fa fa-check" aria-hidden="true" />
  );

  return (
    <div
      className={cx("parameter-apply-button", { "parameter-apply-button--inline": inline })}
      data-show={!!paramCount}
      data-test="ParameterApplyButton">
      <Badge count={paramCount}>
        <Tooltip title={`${KeyboardShortcuts.modKey} + Enter`}>
          <span>
            <Button size={inline ? "small" : "default"} onClick={onClick}>
              {icon} Apply Changes
            </Button>
          </span>
        </Tooltip>
      </Badge>
    </div>
  );
}

ParameterApplyButton.propTypes = {
  onClick: PropTypes.func.isRequired,
  paramCount: PropTypes.number.isRequired,
  inline: PropTypes.bool,
};

ParameterApplyButton.defaultProps = {
  inline: false,
};

export default ParameterApplyButton;
