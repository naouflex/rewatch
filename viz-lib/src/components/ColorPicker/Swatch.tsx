import { isString } from "lodash";
import React from "react";
import cx from "classnames";
import Tooltip from "antd/lib/tooltip";

import "./swatch.less";

type Props = {
  className?: string | null;
  style?: any;
  title?: string | null;
  color?: string | null;
  size?: number;
  [key: string]: any;
};

export default function Swatch({
  className = null,
  color = "transparent",
  title = null,
  size = 12,
  style = null,
  ...props
}: Props) {
  const result = (
    <span
      className={cx("color-swatch", className)}
      style={{ backgroundColor: color, width: size, ...style }}
      {...props}
    />
  );

  if (isString(title) && title !== "") {
    return (
      <Tooltip title={title} mouseEnterDelay={0} mouseLeaveDelay={0}>
        {result}
      </Tooltip>
    );
  }
  return result;
}
