import React from "react";
import PropTypes from "prop-types";
import cx from "classnames";
import AntCollapse from "antd/lib/collapse";

export default function Collapse({ collapsed, children, className, ...props }) {
  return (
    <AntCollapse
      {...props}
      activeKey={collapsed ? null : "content"}
      className={cx(className, "ant-collapse-headerless")}
      items={[
        {
          key: "content",
          label: "",
          showArrow: false,
          children,
        },
      ]}
    />
  );
}

Collapse.propTypes = {
  collapsed: PropTypes.bool,
  children: PropTypes.node,
  className: PropTypes.string,
};

Collapse.defaultProps = {
  collapsed: true,
  children: null,
  className: "",
};
