import React, { useRef, useMemo } from "react";
import PropTypes from "prop-types";
import { isFunction, get, findIndex } from "lodash";
import Dropdown from "antd/lib/dropdown";
import Typography from "antd/lib/typography";
import { DynamicDateType } from "@/services/parameters/DateParameter";
import { DynamicDateRangeType } from "@/services/parameters/DateRangeParameter";

import ArrowLeftOutlinedIcon from "@ant-design/icons/ArrowLeftOutlined";
import ThunderboltTwoToneIcon from "@ant-design/icons/ThunderboltTwoTone";
import ThunderboltOutlinedIcon from "@ant-design/icons/ThunderboltOutlined";

import "./DynamicButton.less";

const { Text } = Typography;

function DynamicButton({ options, selectedDynamicValue, onSelect, enabled, staticValueLabel }) {
  const menuItems = useMemo(() => {
    const items = options.map((option, index) => ({
      key: `${index}`,
      label: (
        <>
          {option.name} {option.label && <em>{isFunction(option.label) ? option.label() : option.label}</em>}
        </>
      ),
    }));

    if (enabled) {
      items.push({ type: "divider" });
      items.push({
        key: "static",
        label: (
          <>
            <ArrowLeftOutlinedIcon />
            <Text type="secondary">{staticValueLabel}</Text>
          </>
        ),
      });
    }

    return items;
  }, [enabled, options, staticValueLabel]);

  const containerRef = useRef(null);

  return (
    <div ref={containerRef}>
      <div role="presentation" onClick={e => e.stopPropagation()}>
        <Dropdown.Button
          menu={{
            className: "dynamic-menu",
            onClick: ({ key }) => onSelect(get(options, key, "static")),
            selectedKeys: [`${findIndex(options, { value: selectedDynamicValue })}`],
            items: menuItems,
            "data-test": "DynamicButtonMenu",
          }}
          className="dynamic-button"
          placement="bottomRight"
          trigger={["click"]}
          icon={
            enabled ? (
              <ThunderboltTwoToneIcon className="dynamic-icon" />
            ) : (
              <ThunderboltOutlinedIcon className="dynamic-icon" />
            )
          }
          getPopupContainer={() => containerRef.current}
          data-test="DynamicButton"
        />
      </div>
    </div>
  );
}

DynamicButton.propTypes = {
  options: PropTypes.arrayOf(PropTypes.object), // eslint-disable-line react/forbid-prop-types
  selectedDynamicValue: PropTypes.oneOfType([DynamicDateType, DynamicDateRangeType]),
  onSelect: PropTypes.func,
  enabled: PropTypes.bool,
  staticValueLabel: PropTypes.string,
};

DynamicButton.defaultProps = {
  options: [],
  selectedDynamicValue: null,
  onSelect: () => {},
  enabled: false,
  staticValueLabel: "Back to Static Value",
};

export default DynamicButton;
