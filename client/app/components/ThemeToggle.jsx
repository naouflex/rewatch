import React, { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import Switch from "antd/lib/switch";
import MoonFilledIcon from "@ant-design/icons/MoonFilled";
import SunFilledIcon from "@ant-design/icons/SunFilled";
import {
  getResolvedTheme,
  subscribeToTheme,
  toggleTheme,
} from "@/services/theme";

import "./ThemeToggle.less";

export function useResolvedTheme() {
  const [resolved, setResolved] = useState(() => getResolvedTheme());
  useEffect(
    () =>
      subscribeToTheme(({ resolved: next }) => {
        setResolved(next);
      }),
    []
  );
  return resolved;
}

export default function ThemeToggle({ variant, showLabel }) {
  const resolved = useResolvedTheme();
  const isDark = resolved === "dark";
  const label = isDark ? "Switch to light theme" : "Switch to dark theme";

  const onChange = useCallback(() => {
    toggleTheme();
  }, []);

  const switchEl = (
    <Switch
      size="small"
      checked={isDark}
      onChange={onChange}
      aria-label={label}
      title={label}
      checkedChildren={<MoonFilledIcon style={{ fontSize: 10 }} />}
      unCheckedChildren={<SunFilledIcon style={{ fontSize: 10 }} />}
      className="theme-toggle__switch"
    />
  );

  if (variant === "menu-item") {
    return (
      <span className="theme-toggle theme-toggle--menu-item">
        {switchEl}
        <span className="theme-toggle__label">
          {isDark ? "Dark theme" : "Light theme"}
        </span>
      </span>
    );
  }

  return (
    <span className="theme-toggle theme-toggle--inline">
      {switchEl}
      {showLabel && (
        <span className="theme-toggle__label">{isDark ? "Dark" : "Light"}</span>
      )}
    </span>
  );
}

ThemeToggle.propTypes = {
  variant: PropTypes.oneOf(["inline", "menu-item"]),
  showLabel: PropTypes.bool,
};

ThemeToggle.defaultProps = {
  variant: "inline",
  showLabel: false,
};
