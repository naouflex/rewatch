import React from "react";
import PropTypes from "prop-types";
import classNames from "classnames";

import { Dashboard } from "@/services/dashboard";

import "./DashboardThumbnail.less";

export default function DashboardThumbnail({ dashboardId, alt, className, size }) {
  return (
    <img
      src={Dashboard.previewUrl(dashboardId)}
      alt={alt || "Dashboard preview"}
      className={classNames("dashboard-thumbnail", `dashboard-thumbnail--${size}`, className)}
      loading="lazy"
      decoding="async"
    />
  );
}

DashboardThumbnail.propTypes = {
  dashboardId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
  alt: PropTypes.string,
  className: PropTypes.string,
  size: PropTypes.oneOf(["list", "home"]),
};

DashboardThumbnail.defaultProps = {
  alt: "",
  className: null,
  size: "list",
};
