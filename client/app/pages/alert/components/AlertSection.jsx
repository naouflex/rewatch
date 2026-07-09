import React from "react";
import PropTypes from "prop-types";
import cx from "classnames";

import ConfigSection from "@/components/ConfigSection/ConfigSection";

import "@/components/ConfigSection/ConfigSection.less";

export default function AlertSection(props) {
  const { className, ...rest } = props;
  return <ConfigSection className={cx("config-section", "alert-section", className)} {...rest} />;
}

AlertSection.propTypes = ConfigSection.propTypes;
AlertSection.defaultProps = ConfigSection.defaultProps;
